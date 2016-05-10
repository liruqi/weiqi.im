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

from tornado.web import HTTPError
from weiqi import settings
from weiqi.handler.base import BaseHandler
from weiqi.models import User, RoomUser, Room
from weiqi.rating import min_rating
from weiqi.glicko2 import Player
from weiqi.recaptcha import validate_recaptcha
from weiqi.mailer import send_mail


class SignUpHandler(BaseHandler):
    def post(self):
        validate_recaptcha(self.get_body_argument('recaptcha'))

        user = User(display=self.get_body_argument('display'),
                    email=self.get_body_argument('email'),
                    is_active=False)

        user.set_password(self.get_body_argument('password'))
        self._sign_up_rating(user, self.get_body_argument('rank'))
        self._sign_up_rooms(user)

        self.db.add(user)
        self.db.commit()

        token = user.auth_token()
        url = '%s://%s/api/auth/sign-up/confirm/%d/%s' % (
            self.request.protocol, self.request.host, user.id, token)

        msg = ('You signed up on weiqi.gs\n'
               'In order to activate your account and login please follow this link:\n\n%s') % url

        send_mail(user.email, user.display, 'Account activation', msg)

        self.write({})

    def _sign_up_rating(self, user, rank):
        rating = min_rating(rank)

        if rating < min_rating('20k') or rating > min_rating('3d'):
            raise HTTPError(400, 'invalid rank')

        user.rating = rating
        user.rating_data = Player(rating)

    def _sign_up_rooms(self, user):
        for room in self.db.query(Room).filter_by(type='main', is_default=True):
            ru = RoomUser(user=user, room=room)
            self.db.add(ru)


class SignUpConfirmHandler(BaseHandler):
    def get(self, user_id, token):
        user = self.db.query(User).get(user_id)

        if not user or not user.check_auth_token(token):
            raise HTTPError(404)

        user.is_active = True
        self.db.commit()

        self.set_secure_cookie(settings.COOKIE_NAME, str(user.id))
        self.redirect('/')


class SignInHandler(BaseHandler):
    def post(self):
        email = self.get_body_argument('email')
        password = self.get_body_argument('password')

        user = self.db.query(User).filter_by(email=email).one()

        if not user.check_password(password):
            raise HTTPError(403, 'invalid username or password')

        if not user.is_active:
            raise HTTPError(403, 'account not activated')

        self.set_secure_cookie(settings.COOKIE_NAME, str(user.id))
        self.write({})


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect('/')


class PasswordResetHandler(BaseHandler):
    def post(self):
        email = self.get_body_argument('email')
        user = self.db.query(User).filter_by(email=email).first()

        if not user:
            return

        token = user.auth_token()
        url = '%s://%s/api/auth/password-reset/confirm/%d/%s' % (
            self.request.protocol, self.request.host, user.id, token)

        msg = ('You have requested a password reset.\n'
               'To reset your password and set a new one please follow this link:\n\n%s\n\n'
               'If you have not made such a request or made it by mistake please ignore this email.') % url

        send_mail(user.email, user.display, 'Password reset', msg)


class PasswordResetConfirmHandler(BaseHandler):
    def get(self, user_id, token):
        messages = []
        user = self.db.query(User).get(user_id)

        if not user or not user.check_auth_token(token):
            show_form = False
            messages.append({'type': 'danger', 'message': 'Token is invalid or user was not found.'})
        else:
            show_form = True

        self.render("password_reset.html", messages=messages, show_form=show_form)

    def post(self, user_id, token):
        messages = []
        show_form = True

        user = self.db.query(User).filter_by(id=user_id).one()

        password = self.get_body_argument('password')
        password_confirm = self.get_body_argument('password-confirm')

        if password != password_confirm:
            messages.append({'type': 'danger', 'message': 'Passwords do not match'})
        else:
            user.set_password(password)
            messages.append({'type': 'success', 'message': 'Password reset'})
            show_form = False

        self.render("password_reset.html", messages=messages, show_form=show_form)
