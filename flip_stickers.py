"""Load optional Telegram file IDs for the generated UNO Flip stickers."""

import json
import logging
import os
from pathlib import Path


logger = logging.getLogger(__name__)
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "images" / "flip" / \
    "sticker_ids.json"


def _load_manifest():
    manifest_path = Path(os.getenv("FLIP_STICKER_MANIFEST",
                                   str(DEFAULT_MANIFEST)))
    try:
        with manifest_path.open("r", encoding="utf-8") as manifest_file:
            return json.load(manifest_file)
    except FileNotFoundError:
        logger.info("UNO Flip sticker manifest not found at %s; using text",
                    manifest_path)
    except (OSError, ValueError) as error:
        logger.warning("Cannot load UNO Flip sticker manifest %s: %s",
                       manifest_path, error)
    return {"normal": {"light": {}, "dark": {}},
            "not_playable": {"light": {}, "dark": {}}}


STICKER_IDS = _load_manifest()


def get_flip_sticker(card, side, playable=True):
    """Return the cached Telegram sticker ID, or ``None`` as a fallback."""
    group = "normal" if playable else "not_playable"
    try:
        return STICKER_IDS[group][side].get(str(card))
    except (AttributeError, KeyError, TypeError):
        return None
