# -*- coding: utf-8 -*-`
"""
project name: guess-a-game
game: tic-tac-toe
"""
import re
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import Result, User, Game, Score, StringMessage, NewGameForm, GameForm, MakeMoveForm, ScoreForms, BoardMessage

from utils import get_by_urlsafe, get_endpoints_current_user

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_WINNING_CHANCE = 'WINNING_CHANCE'

@endpoints.api(name='tic_tac_toe', version='v1')
class TicTacToeApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """
        Args:
            request: The USER_REQUEST objects, which includes a users
                chosen name and an optional email.
        Returns:
            StringMessage: A message that is sent to the client, saying that
                the user has been created.
        Raises:
            endpoints.ConflictException: If the user already exists.
        """
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
            ### user is the one for the first move in the new game
            game = Game.new_game(user=user.key, user_tic=request.user_tic, 
              opponent=opponent.key, opponent_tic=request.opponent_tic, 
              user_of_next_move=user.key)
        except ValueError:
            raise endpoints.BadRequestException('Value Error')

        # Use a task queue to cache winning chance
        taskqueue.add(url='/tasks/cache_winning_chance')
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
            raise endpoints.ForbiddenException('Illegal action: Game is already over.')
            return game.to_form('Game already over!')

        if request.user_of_move!= game.user.get().name and request.user_of_move!= game.opponent.get().name:
              raise endpoints.NotFoundException(
                    'A User with that name %s are not players of current game' % request.user_of_move)

        user_of_move_key = User.query(User.name == request.user_of_move)
        user_of_move = user_of_move_key.get()
        
        if not user_of_move:
            raise endpoints.NotFoundException(
                    'A User with that name %s does not exist!' % request.user_of_move)

        if game.user_of_next_move.get().name != request.user_of_move:
            raise endpoints.NotFoundException(
                    'A User with that name %s is not the game of the current move' % request.user_of_move)
            return game.to_form('It is not your turn!')
        
        ### request.position is integer as defined in models.py
        new_position = request.position
        
        board_state_list = list(game.board_state)

        free_indices = [match.start()
                                for match in re.finditer("-", game.board_state)]
        if new_position not in free_indices:
            return game.to_form("position has already been taken! Choose another position" % new_position)


        if request.user_of_move == game.user.get().name:
            board_state_list[new_position] = game.user_tic
            game.user_of_next_move = game.opponent
        else:
            board_state_list[new_position] = game.opponent_tic
            game.user_of_next_move = game.user

        new_board_state = "".join(board_state_list)
        game.board_state = new_board_state

        ### after every successful move, check the board board_state
        ### check whether some one has won, or a tie
        game_result = game.judge_game()
        game.put()
        if game_result["end"]: 
            if game_result["result"] =="TIE":
                return game.to_form("Game Over, it is a tie!")
            else:
                return game.to_form("Game Over, %s has won" % game_result["winner"])

        
        return game.to_form("Next move: %s" % game.user_of_next_move.get().name)


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

    @endpoints.method(response_message=StringMessage,
                      path='games/winning_chance',
                      name='get_winning_chance',
                      http_method='GET')
    def get_winning_chance(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_WINNING_CHANCE) or '')

    @staticmethod
    def _cache_winning_chance():
        """Populates memcache with the average moves remaining of Games"""
        current_user = get_endpoints_current_user()
        scores = Score.query(Score.user.name == current_user.name).fetch()
        if scores:
            count = 2*len(scores)
            wins = sum([score.result for score in scores])
            chance = wins/float(count)
            
            memcache.set(MEMCACHE_WINNING_CHANCE,
                         'The winning chance is {:.2f}'.format(chance))


##add tic-tac-toe 
api = endpoints.api_server([TicTacToeApi])
