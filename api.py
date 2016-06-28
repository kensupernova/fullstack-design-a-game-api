# -*- coding: utf-8 -*-`
"""
project name: guess-a-game
game: tic-tac-toe
"""
import random
import re
import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms
from models import BoardMessage

# from models import ScoresListRequestMessage
# from models import ScoresListResponseMessage
# from models import ScoreRequestMessage
# from models import ScoreResponseMessage

from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'

@endpoints.api(name='tic_tac_toe', version='v1')
class TicTacToeApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name %s does not exist!' % request.user_name)
        
        ### user b is another user online
        opponent = User.query(User.name == request.opponent_name).get()
        if not opponent:
            raise endpoints.NotFoundException(
                    'A User with that name %s does not exist!' % request.opponent_name)

        try:

            game = Game.new_game(user=user.key, user_tic=request.user_tic, 
              opponent=opponent.key, opponent_tic=request.opponent_tic, 
              user_of_next_move=request.user_of_next_move)
        except ValueError:
            raise endpoints.BadRequestException('Value Error')

        # Use a task queue to update the board state
        ## taskqueue.add(url='/tasks/cache_board_state')
        return game.to_form('Good luck playing Tic-Tac-Toe!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game board_state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game board_state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            return game.to_form('Game already over!')

        if request.user_of_move!= game.user.name and request.user_of_move!= game.opponent.name:
              raise endpoints.NotFoundException(
                    'A User with that name %s are not players of current game' % request.user_of_move)

        user_of_move = User.query(User.name == request.user_of_move).get()
        
        if not user_of_move:
            raise endpoints.NotFoundException(
                    'A User with that name %s does not exist!' % request.user_of_move)
        

        new_position = int(request.position)
        board_state_list = list(game.board_state)

        free_indices = [match.start()
                                for match in re.finditer("-", game.board_state)]
        if new_position not in free_indices:
            return game.to_form("position has already been taken! Choose another position" % new_position)


        if request.user_of_move == game.user.name:
            board_state_list[new_position] = game.user_tic
            game.user_of_next_move = game.opponent
        else:
            board_state_list[new_position] = game.opponent_tic
            game.user_of_next_move = game.user

        new_board_state = "".join(board_state_list)
        game.board_state = new_board_state

        ### after every successful move, check the board board_state
        ### check whether some one has won, or a tie
        game_result = game.judge_win()
        if game_result["end"]: 
            if game_result["winner"] =="TIE":
                game.to_form("Game Over, it is a tie!")
            else:
                game.to_form("Game Over, %s has won" % game_result["winner"])

        game.put()


    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])


##add tic-tac-toe api
api = endpoints.api_server([TicTacToeApi])
