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

from weiqi.test import BaseTestCase
from weiqi.models import User


class TestSignUp(BaseTestCase):
    def test_sign_up(self):
        self.app.post('/api/auth/sign-up', data={
            'display': 'name',
            'email': 'test@test.test',
            'password': 'test',
            'rating': 100,
        })

        user = User.query.filter_by(email='test@test.test').first()

        self.assertIsNotNone(user)
        self.assertEqual(user.display, 'name')
        self.assertEqual(user.email, 'test@test.test')
        self.assertTrue(user.check_password('test'))
        self.assertEqual(user.rating, 100)