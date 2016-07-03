#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging

import webapp2
from google.appengine.api import mail, app_identity
from api import TicTacToeApi

from models import User, Game
from utils import get_endpoints_current_user


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()
        active_games = Game.query().filter(Game.game_over != True)
        
        if active_games:
            for game in active_games:
                if not game.is_canceled:
                    user = game.user.get()
                    if user.email is not None:
                    
                        subject = 'This is a reminder!'
                        body = 'Hello {}, You have an unfinished Tic-Tac-Toe! urlsafe_game_key is {}'.format(user.name, game.key.urlsafe())
                        # This will send test emails, the arguments to send_mail are:
                        # from, to, subject, body
                        mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                                       user.email,
                                       subject,
                                       body)


class UpdateWinningChance(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        TicTacToeApi._cache_winning_chance()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_winning_chance', UpdateWinningChance),
], debug=True)
