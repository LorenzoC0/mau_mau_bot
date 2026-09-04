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


from random import shuffle
import logging

import card as c
from card import Card
from errors import DeckEmptyError
from flip_pairs import FLIP_PAIRS


class Deck(object):
    """ This class represents a deck of cards """

    def __init__(self):
        self.cards = list()
        self.graveyard = list()
        self.logger = logging.getLogger(__name__)

        self.logger.debug(self.cards)

    def shuffle(self):
        """Shuffles the deck"""
        self.logger.debug("Shuffling Deck")
        shuffle(self.cards)

    def draw(self):
        """Draws a card from this deck"""
        try:
            card = self.cards.pop()
            self.logger.debug("Drawing card " + str(card))
            return card
        except IndexError:
            if len(self.graveyard):
                while len(self.graveyard):
                    self.cards.append(self.graveyard.pop())
                self.shuffle()
                return self.draw()
            else:
                raise DeckEmptyError()

    def dismiss(self, card):
        """Returns a card to the deck"""
        # After an UNO Flip, last_card points to the previous discard card,
        # which is already in the graveyard. Do not add the same physical
        # card twice: Deck.flip() must toggle every card exactly once.
        if card and any(discarded is card for discarded in self.graveyard):
            return
        if card and card.special:
            card.color = None
        if card:
            self.graveyard.append(card)

    def _fill_classic_(self):
        # Fill deck with the classic card set
        self.cards.clear()
        self.graveyard.clear()
        for color in c.COLORS:
            for value in c.VALUES:
                self.cards.append(Card(color, value))
                if not value == c.ZERO:
                    self.cards.append(Card(color, value))
        for special in c.SPECIALS:
            for _ in range(4):
                self.cards.append(Card(None, None, special=special))
        self.shuffle()

    def _fill_wild_(self):
        # Fill deck with a wild card set
        self.cards.clear()
        self.graveyard.clear()
        for color in c.COLORS:
            for value in c.WILD_VALUES:
                for _ in range(4):
                    self.cards.append(Card(color, value))
        for special in c.SPECIALS:
            for _ in range(6):
                self.cards.append(Card(None, None, special=special))
        self.shuffle()

    def _fill_flip_(self):
        """Build the 112 physical double-sided UNO Flip cards."""
        self.cards.clear()
        self.graveyard.clear()
        def make_face(face):
            color, value = face
            if value in c.FLIP_SPECIALS:
                return (None, None, value)
            return (color, value, None)

        self.cards = [Card(*make_face(light), dark=make_face(dark))
                      for light, dark in FLIP_PAIRS]
        self.shuffle()

    def flip(self):
        for card in self.cards + self.graveyard:
            card.flip()
