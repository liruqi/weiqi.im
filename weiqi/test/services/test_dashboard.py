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

from datetime import datetime, timedelta
from weiqi.services import DashboardService
from weiqi.test.factories import GameFactory, DemoGameFactory


def test_popular_games_ratings(db):
    demo = DemoGameFactory(demo_owner_rating=1000)
    game = GameFactory(black_rating=1200, white_rating=500)

    svc = DashboardService(db)
    popular = svc.execute('popular_games')

    assert len(popular) == 2
    assert popular[0]['id'] == game.id
    assert popular[1]['id'] == demo.id


def test_popular_games_age(db):
    demo = DemoGameFactory(demo_owner_rating=1000)
    game = GameFactory(black_rating=1200, white_rating=500)
    GameFactory(created_at=datetime.utcnow()-timedelta(days=30))

    svc = DashboardService(db)
    popular = svc.execute('popular_games')

    assert len(popular) == 2
    assert popular[0]['id'] == game.id
    assert popular[1]['id'] == demo.id


def test_popular_games_not_private(db):
    demo = DemoGameFactory(demo_owner_rating=1000)
    game = GameFactory(black_rating=1200, white_rating=500)
    private_game = GameFactory(black_rating=1200, white_rating=500, is_private=True)

    svc = DashboardService(db)
    popular = svc.execute('popular_games')

    assert len(popular) == 2
    assert popular[0]['id'] == game.id
    assert popular[1]['id'] == demo.id
