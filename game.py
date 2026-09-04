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


import logging
from config import ADMIN_LIST, OPEN_LOBBY, DEFAULT_GAMEMODE, ENABLE_TRANSLATIONS
from datetime import datetime

from deck import Deck
import card as c

class Game(object):
    """ This class represents a game of UNO """
    current_player = None
    reversed = False
    choosing_color = False
    started = False
    draw_counter = 0
    players_won = 0
    starter = None
    mode = DEFAULT_GAMEMODE
    job = None
    owner = ADMIN_LIST
    open = OPEN_LOBBY
    translate = ENABLE_TRANSLATIONS

    def __init__(self, chat):
        self.chat = chat
        self.current_player = None
        self.reversed = False
        self.choosing_color = False
        self.started = False
        self.draw_counter = 0
        self.players_won = 0
        self.starter = None
        self.mode = DEFAULT_GAMEMODE
        self.job = None
        self.owner = list(ADMIN_LIST or [])
        self.open = OPEN_LOBBY
        self.translate = ENABLE_TRANSLATIONS
        self.last_card = None
        self.side = 'light'
        self.draw_until_color = False

        self.deck = Deck()

        self.logger = logging.getLogger(__name__)

    @property
    def players(self):
        """Returns a list of all players in this game"""
        players = list()
        if not self.current_player:
            return players

        current_player = self.current_player
        itplayer = current_player.next
        players.append(current_player)
        while itplayer and itplayer != current_player:
            players.append(itplayer)
            itplayer = itplayer.next
        return players

    @property
    def is_flip(self):
        """Whether this game uses UNO Flip rules, regardless of presentation."""
        return self.mode in ('flip', 'flip_text')

    def start(self):
        if self.is_flip:
            self.deck._fill_flip_()
        elif self.mode == None or self.mode != "wild":
            self.deck._fill_classic_()
        else:
            self.deck._fill_wild_()

        self._first_card_()
        self.started = True

    def set_mode(self, mode):
        self.mode = mode

    def reverse(self):
        """Reverses the direction of game"""
        self.reversed = not self.reversed

    @property
    def colors(self):
        return (c.BLUE, c.GREEN, c.RED, c.YELLOW) if self.side == 'light' else \
            (c.PINK, c.TEAL, c.ORANGE, c.PURPLE)

    def turn(self):
        """Marks the turn as over and change the current player"""
        self.logger.debug("Next Player")
        self.current_player = self.current_player.next
        self.current_player.drew = False
        self.current_player.turn_started = datetime.now()
        self.choosing_color = False

    def _first_card_(self):
        # In case that the player did not select a game mode
        if not self.deck.cards:
            self.set_mode(DEFAULT_GAMEMODE)

        rejected = []
        while True:
            first_card = self.deck.draw()
            is_flip_action = self.is_flip and \
                (first_card.special or first_card.value not in c.NUMBERS)
            if first_card.special or is_flip_action:
                rejected.append(first_card)
                continue
            break

        # Rejected opening cards belong to the draw pile, not the discard pile.
        self.deck.cards.extend(rejected)
        self.deck.shuffle()

        # There is no previous discard when the opening card is placed.
        self.last_card = None
        self.play_card(first_card)

    def play_card(self, card):
        """
        Plays a card and triggers its effects.
        Should be called only from Player.play or on game start to play the
        first card
        """
        self.deck.dismiss(self.last_card)
        self.last_card = card
        played_value = card.value
        played_special = card.special

        self.logger.info("Playing card " + repr(card))
        if played_value == c.SKIP:
            self.turn()
        elif played_special == c.DRAW_FOUR:
            self.draw_counter += 4
            self.logger.debug("Draw counter increased by 4")
        elif played_special == c.WILD_DRAW_TWO:
            self.draw_counter += 2
        elif played_value == c.DRAW_ONE:
            self.draw_counter += 1
        elif played_value == c.DRAW_FIVE:
            self.draw_counter += 5
        elif played_value == c.SKIP_EVERYONE:
            for _ in range(max(0, len(self.players) - 1)):
                self.turn()
        elif played_value == c.DRAW_TWO:
            self.draw_counter += 2
            self.logger.debug("Draw counter increased by 2")
        elif played_value == c.REVERSE:
            # Special rule for two players
            if self.current_player == self.current_player.next.next:
                self.turn()
            else:
                self.reverse()

        if played_special == c.DRAW_COLOR:
            self.draw_until_color = True

        if played_value == c.FLIP:
            self.deck.dismiss(card)
            self.deck.flip()
            # Flipping a physical pile reverses its order. Keep the newly
            # exposed top card outside the recyclable discard pile.
            self.deck.graveyard.reverse()
            self.last_card = self.deck.graveyard.pop()
            for player in self.players:
                for hand_card in player.cards:
                    hand_card.flip()
            self.side = 'dark' if self.side == 'light' else 'light'

        # Don't turn if the current player has to choose a color
        if played_special not in (c.CHOOSE, c.DRAW_FOUR, c.WILD_DRAW_TWO,
                                  c.DRAW_COLOR):
            self.turn()
        else:
            self.logger.debug("Choosing Color...")
            self.choosing_color = True

    def choose_color(self, color):
        """Carries out the color choosing and turns the game"""
        self.last_card.color = color
        self.turn()
