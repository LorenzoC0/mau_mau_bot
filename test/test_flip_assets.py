#!/usr/bin/env python3

import json
from pathlib import Path
import unittest

from deck import Deck


class FlipAssetsTest(unittest.TestCase):

    def test_manifest_covers_every_visible_face(self):
        project_dir = Path(__file__).resolve().parents[1]
        images_dir = project_dir / "images"
        manifest = json.loads(
            (images_dir / "flip" / "asset_manifest.json").read_text(
                encoding="utf-8"))

        deck = Deck()
        deck._fill_flip_()
        expected_light = {str(card) for card in deck.cards}
        for card in deck.cards:
            card.flip()
        expected_dark = {str(card) for card in deck.cards}

        self.assertEqual(len(expected_light), 54)
        self.assertEqual(len(expected_dark), 54)
        for group in ("normal", "not_playable"):
            self.assertSetEqual(expected_light,
                                set(manifest[group]["light"]))
            self.assertSetEqual(expected_dark,
                                set(manifest[group]["dark"]))

            for side in ("light", "dark"):
                for relative_path in manifest[group][side].values():
                    sticker = images_dir / relative_path
                    self.assertTrue(sticker.is_file(), sticker)
                    self.assertLessEqual(sticker.stat().st_size, 512 * 1024)
                    with sticker.open("rb") as sticker_file:
                        header = sticker_file.read(12)
                    self.assertEqual(header[:4], b"RIFF")
                    self.assertEqual(header[8:12], b"WEBP")


if __name__ == "__main__":
    unittest.main()
