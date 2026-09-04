#!/usr/bin/env python3
"""Publish generated UNO Flip assets using the Telegram Bot API.

Required environment variables:
    TOKEN                 Bot token from BotFather
    TELEGRAM_USER_ID      Numeric ID of the sticker-set owner

The owner must have sent at least one message to the bot before running this
script. No Telegram user login, phone number, api_id or api_hash is required.
"""

import argparse
import json
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


IMAGES_DIR = Path(__file__).resolve().parent
FLIP_DIR = IMAGES_DIR / "flip"
ASSET_MANIFEST = FLIP_DIR / "asset_manifest.json"
ID_MANIFEST = FLIP_DIR / "sticker_ids.json"
INITIAL_SET_SIZE = 50


class TelegramApiError(RuntimeError):
    pass


class BotApi:
    def __init__(self, token):
        self.base_url = f"https://api.telegram.org/bot{token}/"

    def call(self, method, fields=None, file_field=None):
        fields = fields or {}
        if file_field:
            body, content_type = self._multipart(fields, *file_field)
        else:
            body = urlencode(fields).encode("utf-8")
            content_type = "application/x-www-form-urlencoded"

        request = Request(self.base_url + method, data=body,
                          headers={"Content-Type": content_type})
        try:
            with urlopen(request, timeout=90) as response:
                payload = json.load(response)
        except HTTPError as error:
            try:
                payload = json.load(error)
            except Exception:
                raise TelegramApiError(f"HTTP {error.code} calling {method}")

        if not payload.get("ok"):
            raise TelegramApiError(
                f"{method}: {payload.get('description', 'unknown error')}")
        return payload["result"]

    @staticmethod
    def _multipart(fields, field_name, path):
        boundary = "----MauMauBot" + uuid4().hex
        chunks = []
        for name, value in fields.items():
            chunks.extend((
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"), b"\r\n",
            ))

        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend((
            f"--{boundary}\r\n".encode(),
            (f'Content-Disposition: form-data; name="{field_name}"; '
             f'filename="{path.name}"\r\n').encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            path.read_bytes(), b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ))
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def pack_name(base_name, bot_username):
    suffix = f"_by_{bot_username}"
    name = base_name if base_name.lower().endswith(suffix.lower()) else \
        base_name + suffix
    if len(name) > 64:
        raise ValueError(f'Sticker pack name "{name}" exceeds 64 characters')
    return name


def ordered_assets(asset_manifest, group):
    for side in ("light", "dark"):
        for key, relative_path in asset_manifest[group][side].items():
            yield side, key, IMAGES_DIR / relative_path


def upload_file(api, owner_id, path):
    result = api.call(
        "uploadStickerFile",
        {"user_id": owner_id, "sticker_format": "static"},
        ("sticker", path),
    )
    return result["file_id"]


def input_sticker(file_id):
    return {"sticker": file_id, "format": "static",
            "emoji_list": ["🃏"]}


def set_exists(api, name):
    try:
        api.call("getStickerSet", {"name": name})
        return True
    except TelegramApiError as error:
        if "STICKERSET_INVALID" in str(error):
            return False
        raise


def publish_group(api, owner_id, name, title, assets, replace=False):
    if set_exists(api, name):
        if not replace:
            raise TelegramApiError(
                f'{name} already exists; rerun with --replace to recreate it')
        print(f"Deleting existing pack {name}")
        api.call("deleteStickerSet", {"name": name})

    uploaded = []
    total = len(assets)
    for index, (side, key, path) in enumerate(assets, start=1):
        if not path.is_file():
            raise FileNotFoundError(path)
        print(f"[{index:03}/{total}] Uploading {side}/{key}")
        uploaded.append((side, key, upload_file(api, owner_id, path)))

    first = [input_sticker(file_id)
             for _, _, file_id in uploaded[:INITIAL_SET_SIZE]]
    api.call("createNewStickerSet", {
        "user_id": owner_id,
        "name": name,
        "title": title,
        "stickers": json.dumps(first),
        "sticker_type": "regular",
    })
    for _, _, file_id in uploaded[INITIAL_SET_SIZE:]:
        api.call("addStickerToSet", {
            "user_id": owner_id,
            "name": name,
            "sticker": json.dumps(input_sticker(file_id)),
        })

    published = api.call("getStickerSet", {"name": name})["stickers"]
    if len(published) != len(uploaded):
        raise TelegramApiError(
            f"{name}: expected {len(uploaded)} stickers, got {len(published)}")
    return [(side, key, sticker["file_id"])
            for (side, key, _), sticker in zip(uploaded, published)]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-name", default="mau_mau_flip")
    parser.add_argument("--disabled-name", default="mau_mau_flip_disabled")
    parser.add_argument("--normal-title", default="Mau Mau Bot — Flip")
    parser.add_argument("--disabled-title",
                        default="Mau Mau Bot — Flip unavailable")
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    token = os.environ.get("TOKEN")
    owner_id = os.environ.get("TELEGRAM_USER_ID")
    if not token or not owner_id:
        raise SystemExit("TOKEN and TELEGRAM_USER_ID are required")
    owner_id = int(owner_id)

    assets = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    api = BotApi(token)
    bot_username = api.call("getMe")["username"]
    names = {
        "normal": pack_name(args.normal_name, bot_username),
        "not_playable": pack_name(args.disabled_name, bot_username),
    }
    titles = {
        "normal": args.normal_title,
        "not_playable": args.disabled_title,
    }
    ids = {"normal": {"light": {}, "dark": {}},
           "not_playable": {"light": {}, "dark": {}}}

    for group in ("normal", "not_playable"):
        group_assets = list(ordered_assets(assets, group))
        uploaded = publish_group(
            api, owner_id, names[group], titles[group], group_assets,
            replace=args.replace,
        )
        for side, key, file_id in uploaded:
            ids[group][side][key] = file_id
        print(f"Published https://t.me/addstickers/{names[group]}")

    ID_MANIFEST.write_text(json.dumps(ids, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Saved {ID_MANIFEST}")
    print("Rebuild or restart the bot after making this file available to it.")


if __name__ == "__main__":
    main()
