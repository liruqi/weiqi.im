# weiqi.gs
# Copyright (C) 2016 Michael Bitzi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from sqlalchemy.orm import undefer
from contextlib import contextmanager
import random
from datetime import datetime
from tornado import gen
from weiqi.db import transaction, session
from weiqi.services import BaseService, ServiceError, UserService, RatingService, RoomService
from weiqi.models import Game, Timing
from weiqi.board import RESIGN, BLACK, SYMBOL_TRIANGLE, SYMBOL_CIRCLE, SYMBOL_SQUARE
from weiqi.scoring import count_score
from weiqi.timing import update_timing, update_timing_after_move


class InvalidPlayerError(ServiceError):
    pass


class InvalidStageError(ServiceError):
    pass


class GameHasNotStartedError(ServiceError):
    pass


class GameService(BaseService):
    __service_name__ = 'games'

    @BaseService.register
    def open_game(self, game_id):
        game = self.db.query(Game).get(game_id)
        if not game:
            return

        RoomService(self.db, self.socket, self.user).join_room(game.room_id)

        self.subscribe(game.id)
        self.socket.send('game_data', game.to_frontend(full=True))

        if game.is_demo and game.demo_owner == self.user:
            self.socket.publish('game_started', game.to_frontend())


    @BaseService.register
    def close_game(self, game_id):
        game = self.db.query(Game).get(game_id)
        if not game:
            return

        self.unsubscribe(game.id)
        RoomService(self.db, self.socket, self.user).leave_room(game.room_id)

        if game.is_demo and game.demo_owner == self.user:
            self.socket.publish('game_finished', game.to_frontend())

    def subscribe(self, game_id):
        self.socket.subscribe('game_data/'+str(game_id))
        self.socket.subscribe('game_update/'+str(game_id))
        self.socket.subscribe('demo_current_node_id/'+str(game_id))

    def unsubscribe(self, game_id):
        self.socket.unsubscribe('game_data/'+str(game_id))
        self.socket.unsubscribe('game_update/'+str(game_id))
        self.socket.unsubscribe('demo_current_node_id/'+str(game_id))

    def publish_demos(self):
        if not self.user:
            return

        for demo in self.user.open_demos(self.db):
            if self.user.is_online:
                self.socket.publish('game_started', demo.to_frontend())
            else:
                self.socket.publish('game_finished', demo.to_frontend())

    @BaseService.authenticated
    @BaseService.register
    def move(self, game_id, move):
        with self._game_for_update(game_id) as game:
            if game.is_demo:
                self._game_move_demo(game, move)
            else:
                self._game_move(game, move)

                if game.stage == 'finished':
                    self._finish_game(game)

            game.apply_board_change()

            self.db.commit()

            if game.is_demo or game.stage != 'finished':
                self._publish_game_update(game)

    @contextmanager
    def _game_for_update(self, game_id):
        with transaction(self.db):
            game = self.db.query(Game).options(undefer('board')).with_for_update().get(game_id)
            yield game

    def _game_move_demo(self, game, move):
        if not self.user == game.demo_control:
            raise InvalidPlayerError()

        if move == RESIGN:
            raise ServiceError('cannot resign in demo games')

        game.board.play(move)

    def _game_move(self, game, move):
        if self.user not in [game.black_user, game.white_user]:
            raise InvalidPlayerError()

        if game.stage == 'finished':
            raise InvalidStageError()

        if not game.timing.has_started:
            raise GameHasNotStartedError()

        if move == RESIGN:
            self._resign(game)
            return

        if game.stage != 'playing':
            raise InvalidStageError()

        if game.current_user != self.user:
            raise InvalidPlayerError()

        if not update_timing(game.timing, game.board.current == BLACK):
            self._win_by_time(game)
            return

        game.board.play(move)

        update_timing_after_move(game.timing, game.board.current != BLACK)

        if game.board.both_passed:
            game.stage = 'counting'
            self._update_score(game)

    def _resign(self, game):
        game.stage = 'finished'

        if self.user == game.black_user:
            game.result = 'W+R'
        elif self.user == game.white_user:
            game.result = 'B+R'
        else:
            raise InvalidPlayerError()

    def _win_by_time(self, game):
        game.stage = 'finished'
        if game.board.current == BLACK:
            game.result = 'W+T'
        else:
            game.result = 'B+T'

    def _update_score(self, game):
        score = count_score(game.board, game.komi)
        game.result = score.result
        game.board.current_node.score_points = score.points

    def _publish_game_update(self, game):
        self.socket.publish('game_update/'+str(game.id), {
            'game_id': game.id,
            'stage': game.stage,
            'result': game.result,
            'timing': game.timing.to_frontend() if game.timing else None,
            'node': game.board.current_node.to_dict() if game.board.current_node else {},
        })

    @BaseService.authenticated
    @BaseService.register
    def toggle_marked_dead(self, game_id, coord):
        with self._game_for_update(game_id) as game:
            if self.user not in [game.black_user, game.white_user]:
                raise InvalidPlayerError()

            if game.stage != 'counting':
                raise InvalidStageError()

            game.board.toggle_marked_dead(coord)
            self._update_score(game)
            game.apply_board_change()

            self.db.commit()
            self._publish_game_update(game)

    @BaseService.authenticated
    @BaseService.register
    def confirm_score(self, game_id, result):
        with self._game_for_update(game_id) as game:
            if self.user not in [game.black_user, game.white_user]:
                raise InvalidPlayerError()

            if game.stage != 'counting':
                raise InvalidStageError()

            if result != game.result:
                raise ServiceError('got incorrect result: {}'.format(result))

            if self.user == game.black_user:
                game.result_black_confirmed = game.result
            else:
                game.result_white_confirmed = game.result

            if game.result_black_confirmed == game.result_white_confirmed:
                game.stage = 'finished'
                self._finish_game(game)

    def _finish_game(self, game):
        if game.is_demo or game.stage != 'finished':
            return

        if game.is_ranked:
            RatingService(self.db).update_ratings(game)

        self.socket.publish('game_finished', game.to_frontend())
        self._publish_game_data(game)

        UserService(self.db, self.socket, game.black_user).publish_status()
        UserService(self.db, self.socket, game.white_user).publish_status()

    def _publish_game_data(self, game):
        self.socket.publish('game_data/'+str(game.id), game.to_frontend(full=True))

    @BaseService.authenticated
    @BaseService.register
    def set_current_node(self, game_id, node_id):
        game = self.db.query(Game).get(game_id)

        if not game.demo_control == self.user:
            raise InvalidPlayerError()

        if node_id >= len(game.board.tree):
            raise ServiceError('invalid node_id')

        game.board.current_node_id = node_id
        game.apply_board_change()

        self.socket.publish('demo_current_node_id/'+str(game.id), {
            'game_id': game.id,
            'node_id': game.board.current_node_id,
        })

    @BaseService.authenticated
    @BaseService.register
    def demo_tool_triangle(self, game_id, coord):
        with self._demo_tool(game_id) as (game, node):
            node.toggle_symbol(coord, SYMBOL_TRIANGLE)

    @BaseService.authenticated
    @BaseService.register
    def demo_tool_square(self, game_id, coord):
        with self._demo_tool(game_id) as (game, node):
            node.toggle_symbol(coord, SYMBOL_SQUARE)

    @BaseService.authenticated
    @BaseService.register
    def demo_tool_circle(self, game_id, coord):
        with self._demo_tool(game_id) as (game, node):
            node.toggle_symbol(coord, SYMBOL_CIRCLE)

    @BaseService.authenticated
    @BaseService.register
    def demo_tool_label(self, game_id, coord):
        with self._demo_tool(game_id) as (game, node):
            node.toggle_label(coord)

    @BaseService.authenticated
    @BaseService.register
    def demo_tool_number(self, game_id, coord):
        with self._demo_tool(game_id) as (game, node):
            node.toggle_number(coord)

    @BaseService.authenticated
    @BaseService.register
    def demo_tool_edit(self, game_id, coord, color):
        with self._demo_tool(game_id) as (game, node):
            game.board.toggle_edit(coord, color)

    @contextmanager
    def _demo_tool(self, game_id):
        game = self.db.query(Game).options(undefer('board')).get(game_id)

        if not game.is_demo or not game.demo_control == self.user:
            raise InvalidPlayerError()

        if not game.board.current_node:
            game.board.add_edits([], [], [])

        node = game.board.current_node

        yield game, node

        game.apply_board_change()
        self._publish_game_update(game)


    @classmethod
    @gen.coroutine
    def run_time_checker(cls, pubsub):
        """A coroutine which periodically runs `check_due_moves`."""
        from weiqi.handler.socket import SocketMixin

        # Sleep for a random duration so that different processes don't all run at the same time.
        yield gen.sleep(random.random())

        while True:
            with session() as db:
                socket = SocketMixin()
                socket.initialize(pubsub)
                svc = GameService(db, socket)
                svc.check_due_moves()

            yield gen.sleep(1)

    def check_due_moves(self):
        """Checks and updates all timings which are due for a move being played."""
        timings = self.db.query(Timing).with_for_update().join('game').options(undefer('game.board')).filter(
            (Game.is_demo.is_(False)) & (Game.stage == 'playing') & (Timing.next_move_at <= datetime.utcnow()))

        for timing in timings:
            if not update_timing(timing, timing.game.board.current == BLACK):
                self._win_by_time(timing.game)
                self._finish_game(timing.game)
