#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Telegram bot to play UNO in group chats
# Copyright (c) 2016 Jannes Höke <uno@jhoeke.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import unittest

from game import Game
from player import Player
import card as c


class Test(unittest.TestCase):

    game = None

    def setUp(self):
        self.game = Game(None)

    def test_insert(self):
        p0 = Player(self.game, "Player 0")
        p1 = Player(self.game, "Player 1")
        p2 = Player(self.game, "Player 2")

        self.assertEqual(p0, p2.next)
        self.assertEqual(p1, p0.next)
        self.assertEqual(p2, p1.next)

        self.assertEqual(p0.prev, p2)
        self.assertEqual(p1.prev, p0)
        self.assertEqual(p2.prev, p1)

    def test_reverse(self):
        p0 = Player(self.game, "Player 0")
        p1 = Player(self.game, "Player 1")
        p2 = Player(self.game, "Player 2")
        self.game.reverse()
        p3 = Player(self.game, "Player 3")

        self.assertEqual(p0, p3.next)
        self.assertEqual(p1, p2.next)
        self.assertEqual(p2, p0.next)
        self.assertEqual(p3, p1.next)

        self.assertEqual(p0, p2.prev)
        self.assertEqual(p1, p3.prev)
        self.assertEqual(p2, p1.prev)
        self.assertEqual(p3, p0.prev)

    def test_leave(self):
        p0 = Player(self.game, "Player 0")
        p1 = Player(self.game, "Player 1")
        p2 = Player(self.game, "Player 2")

        p1.leave()

        self.assertEqual(p0, p2.next)
        self.assertEqual(p2, p0.next)

    def test_draw(self):
        p = Player(self.game, "Player 0")
        self.game.start()

        deck_before = len(self.game.deck.cards)
        top_card = self.game.deck.cards[-1]

        p.draw()

        self.assertEqual(top_card, p.cards[-1])
        self.assertEqual(deck_before, len(self.game.deck.cards) + 1)

    def test_draw_two(self):
        p = Player(self.game, "Player 0")
        self.game.start()

        deck_before = len(self.game.deck.cards)
        self.game.draw_counter = 2

        p.draw()

        self.assertEqual(deck_before, len(self.game.deck.cards) + 2)

    def test_playable_cards_simple(self):
        p = Player(self.game, "Player 0")

        self.game.last_card = c.Card(c.RED, '5')

        p.cards = [c.Card(c.RED, '0'), c.Card(c.RED, '5'), c.Card(c.BLUE, '0'),
                   c.Card(c.GREEN, '5'), c.Card(c.GREEN, '8')]

        expected = [c.Card(c.RED, '0'), c.Card(c.RED, '5'),
                    c.Card(c.GREEN, '5')]

        self.assertListEqual(p.playable_cards(), expected)

    def test_playable_cards_on_draw_two(self):
        p = Player(self.game, "Player 0")

        self.game.last_card = c.Card(c.RED, c.DRAW_TWO)
        self.game.draw_counter = 2

        p.cards = [c.Card(c.RED, c.DRAW_TWO), c.Card(c.RED, '5'),
                   c.Card(c.BLUE, '0'), c.Card(c.GREEN, '5'),
                   c.Card(c.GREEN, c.DRAW_TWO)]

        expected = [c.Card(c.RED, c.DRAW_TWO), c.Card(c.GREEN, c.DRAW_TWO)]

        self.assertListEqual(p.playable_cards(), expected)

    def test_playable_cards_on_draw_four(self):
        p = Player(self.game, "Player 0")

        self.game.last_card = c.Card(c.RED, None, c.DRAW_FOUR)
        self.game.draw_counter = 4

        p.cards = [c.Card(c.RED, c.DRAW_TWO), c.Card(c.RED, '5'),
                   c.Card(c.BLUE, '0'), c.Card(c.GREEN, '5'),
                   c.Card(c.GREEN, c.DRAW_TWO),
                   c.Card(None, None, c.DRAW_FOUR),
                   c.Card(None, None, c.CHOOSE)]

        expected = list()

        self.assertListEqual(p.playable_cards(), expected)

    def test_passively_exposed_wild_accepts_any_color(self):
        self.game.set_mode('flip')
        p = Player(self.game, "Player 0")
        exposed_wild = c.Card(c.RED, c.ONE,
                              dark=(None, None, c.DRAW_COLOR))
        exposed_wild.flip()
        self.game.last_card = exposed_wild
        p.cards = [c.Card(c.BLUE, '2', dark=(c.PINK, '3', None))]

        playable = p.playable_cards()

        self.assertEqual(len(playable), 1)
        self.assertIs(playable[0], p.cards[0])
        self.assertFalse(p.bluffing)

    def test_bluffing(self):
        p = Player(self.game, "Player 0")
        Player(self.game, "Player 01")

        self.game.last_card = c.Card(c.RED, '1')

        p.cards = [c.Card(c.RED, c.DRAW_TWO), c.Card(c.RED, '5'),
                   c.Card(c.BLUE, '0'), c.Card(c.GREEN, '5'),
                   c.Card(c.RED, '5'), c.Card(c.GREEN, c.DRAW_TWO),
                   c.Card(None, None, c.DRAW_FOUR),
                   c.Card(None, None, c.CHOOSE)]

        p.playable_cards()
        self.assertTrue(p.bluffing)

        p.cards = [c.Card(c.BLUE, '1'), c.Card(c.GREEN, '1'),
                   c.Card(c.GREEN, c.DRAW_TWO),
                   c.Card(None, None, c.DRAW_FOUR),
                   c.Card(None, None, c.CHOOSE)]

        p.playable_cards()

        draw_four = next(card for card in p.cards
                         if card.special == c.DRAW_FOUR)
        p.play(draw_four)
        self.game.choose_color(c.GREEN)

        self.assertFalse(self.game.current_player.prev.bluffing)

    def test_bluff_checks_the_whole_hand_after_drawing(self):
        p = Player(self.game, "Player 0")
        self.game.last_card = c.Card(c.RED, c.ONE)
        matching = c.Card(c.RED, '5')
        drawn_wild = c.Card(None, None, c.DRAW_FOUR)
        p.cards = [matching, drawn_wild]
        p.drew = True

        playable = p.playable_cards()

        self.assertTrue(p.bluffing)
        self.assertEqual(len(playable), 1)
        self.assertIs(playable[0], drawn_wild)

    def test_flip_deck_and_side_change(self):
        self.game.set_mode('flip')
        p0 = Player(self.game, "Player 0")
        Player(self.game, "Player 1")
        self.game.start()

        self.assertEqual(len(self.game.deck.cards), 111)
        self.assertEqual(len(self.game.deck.graveyard), 0)
        self.assertEqual(self.game.side, 'light')
        self.assertTrue(all(card._dark for card in self.game.deck.cards))

        p0.cards = [c.Card(c.RED, c.FLIP, dark=(c.PINK, c.FLIP, None))]
        self.game.last_card = c.Card(c.RED, c.ONE,
                                     dark=(c.PINK, c.ONE, None))
        self.game.current_player = p0
        p0.playable_cards()
        p0.play(p0.cards[0])

        self.assertEqual(self.game.side, 'dark')
        self.assertEqual(self.game.last_card.color, c.PINK)

    def test_flip_text_uses_the_same_physical_deck(self):
        self.game.set_mode('flip_text')
        Player(self.game, "Player 0")
        Player(self.game, "Player 1")

        self.game.start()

        self.assertTrue(self.game.is_flip)
        self.assertEqual(len(self.game.deck.cards), 111)
        self.assertTrue(all(card._dark for card in self.game.deck.cards))

    def test_two_flips_restore_the_original_side(self):
        self.game.set_mode('flip')
        p0 = Player(self.game, "Player 0")
        Player(self.game, "Player 1")
        self.game.start()
        original_top = self.game.last_card

        first_flip = c.Card(c.RED, c.FLIP,
                            dark=(c.PINK, c.FLIP, None))
        p0.cards = [first_flip,
                    c.Card(c.RED, c.FLIP, dark=(c.PINK, c.FLIP, None))]
        self.game.current_player = p0

        p0.play(p0.cards[0])
        self.assertEqual(self.game.side, 'dark')
        p0 = self.game.current_player
        p0.cards.append(c.Card(c.PINK, c.FLIP,
                               dark=(c.RED, c.FLIP, None)))
        p0.cards[-1].side = 'dark'
        p0.play(p0.cards[-1])

        self.assertEqual(self.game.side, 'light')
        self.assertEqual(self.game.last_card.side, 'light')
        self.assertIs(self.game.last_card, first_flip)
        self.assertEqual(len(self.game.deck.graveyard), 2)

    def test_draw_until_color_is_cleared_if_deck_runs_out(self):
        from errors import DeckEmptyError

        p = Player(self.game, "Player 0")
        self.game.last_card = c.Card(c.RED, c.ONE)
        self.game.draw_until_color = True
        self.game.deck.cards = [c.Card(c.BLUE, '2')]

        with self.assertRaises(DeckEmptyError):
            p.draw()

        self.assertFalse(self.game.draw_until_color)

    def test_flip_reverses_the_physical_discard_pile(self):
        self.game.set_mode('flip')
        p0 = Player(self.game, "Player 0")
        Player(self.game, "Player 1")

        bottom = c.Card(c.RED, c.ONE, dark=(c.PINK, '2', None))
        middle = c.Card(c.BLUE, '3', dark=(c.TEAL, '4', None))
        top = c.Card(c.GREEN, '5', dark=(c.ORANGE, '6', None))
        flip = c.Card(c.GREEN, c.FLIP, dark=(c.PURPLE, c.FLIP, None))
        self.game.deck.graveyard = [bottom, middle]
        self.game.last_card = top
        self.game.current_player = p0
        p0.cards = [flip]

        p0.play(flip)

        self.assertIs(self.game.last_card, bottom)
        self.assertEqual(self.game.side, 'dark')
        self.assertListEqual(
            [id(card) for card in self.game.deck.graveyard],
            [id(flip), id(top), id(middle)]
        )
        self.assertTrue(all(card.side == 'dark'
                            for card in self.game.deck.graveyard))

    def test_play_removes_the_selected_physical_card(self):
        self.game.set_mode('flip')
        p0 = Player(self.game, "Player 0")
        Player(self.game, "Player 1")
        self.game.last_card = c.Card(c.RED, c.ONE,
                                     dark=(c.PINK, c.ONE, None))
        self.game.current_player = p0

        first = c.Card(c.RED, '2', dark=(c.PINK, '3', None))
        selected = c.Card(c.RED, '2', dark=(c.TEAL, '4', None))
        p0.cards = [first, selected]

        p0.play(selected)

        self.assertTrue(any(card is first for card in p0.cards))
        self.assertFalse(any(card is selected for card in p0.cards))
        self.assertIs(self.game.last_card, selected)

    def test_flip_does_not_activate_its_hidden_action(self):
        self.game.set_mode('flip')
        p0 = Player(self.game, "Player 0")
        p1 = Player(self.game, "Player 1")
        self.game.last_card = c.Card(c.RED, c.ONE,
                                     dark=(c.PINK, c.ONE, None))
        self.game.current_player = p0

        flip = c.Card(c.RED, c.FLIP,
                      dark=(None, None, c.DRAW_COLOR))
        p0.cards = [flip, c.Card(c.BLUE, '2',
                                 dark=(c.TEAL, '3', None))]

        p0.play(flip)

        self.assertFalse(self.game.choosing_color)
        self.assertIs(self.game.current_player, p1)

    def test_game_state_is_not_shared_between_instances(self):
        other = Game(None)
        self.game.set_mode('flip')
        self.game.reverse()
        self.game.choosing_color = True
        self.game.owner.append(123)

        self.assertNotEqual(other.mode, 'flip')
        self.assertFalse(other.reversed)
        self.assertFalse(other.choosing_color)
        self.assertNotIn(123, other.owner)
