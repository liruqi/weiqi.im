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

from weiqi.handler.base import BaseHandler
from weiqi.identicon import generate_identicon


class IndexHandler(BaseHandler):
    def get(self):
        self.render("index.html")


class PingHandler(BaseHandler):
    def get(self):
        self.write('pong')


class AvatarHandler(BaseHandler):
    def get(self, user_id):
        identicon = generate_identicon(user_id.encode())

        self.set_header('Content-Type', 'image/png')
        self.write(identicon.read())