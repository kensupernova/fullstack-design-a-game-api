# -*- coding: utf-8 -*-`
"""
project name: guess-a-game
game: tic-tac-toe
"""
import re
from collections import defaultdict
import operator
import json
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import Result, User, Game, Score, StringMessage, NewGameForm, GameForm, MakeMoveForm, ScoreForms, BoardMessage, GameForms, UserTotalScoreForm, UserTotalScoreForms

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
        """Return the current game"""
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
        """Makes a move in tic-tac-toe"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            return game.to_form('Game already over!')
            raise endpoints.ForbiddenException('Illegal action: Game is already over.')
            

        if request.user_of_move!= game.user.get().name and request.user_of_move!= game.opponent.get().name:
              raise endpoints.NotFoundException(
                    'A User with that name %s are not players of current game' % request.user_of_move)

        user_of_move_key = User.query(User.name == request.user_of_move)
        user_of_move = user_of_move_key.get()
        
        if not user_of_move:
            raise endpoints.NotFoundException(
                    'User %s does not exist!' % request.user_of_move)

        if game.user_of_next_move.get().name != request.user_of_move:
            return game.to_form('User %s is not the game of the current move, %s please!' % (request.user_of_move, game.user_of_next_move.get().name))
            
            raise endpoints.NotFoundException(
                    'User %s is not the game of the current move, %s please!' % (request.user_of_move, game.user_of_next_move.get().name))
            
        
        ### request.position is integer as defined in models.py
        new_position = request.position
        
        board_state_list = list(game.board_state)

        free_indices = [match.start()
                                for match in re.finditer("-", game.board_state)]
        if new_position not in free_indices:
            return game.to_form("position has already been taken! %s Choose another position" % new_position)


        if request.user_of_move == game.user.get().name:
            board_state_list[new_position] = game.user_tic
            game.user_of_next_move = game.opponent
        else:
            board_state_list[new_position] = game.opponent_tic
            game.user_of_next_move = game.user

        new_board_state = "".join(board_state_list)
        game.board_state = new_board_state

        ## after each move, record history
        game.history += "(%s,%s)," %(request.user_of_move, request.position)

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

    @endpoints.method(
        request_message=endpoints.ResourceContainer(
                user_name=messages.StringField(1),),
        response_message=ScoreForms,
        path='scores/user/{user_name}',
        name='get_user_scores',
        http_method='GET')
    def get_user_scores(self, request):
        """Returns a list of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

   

    @endpoints.method(response_message=GameForms,
                      path='games',
                      name='get_games',
                      http_method='GET')
    def get_games(self, request):
        """List all the games"""
        return GameForms(items=[game.to_form("") for game in Game.query()])

    @endpoints.method(response_message=StringMessage,
                      path='users',
                      name='get_users',
                      http_method='GET')
    def get_users(self, request):
        """List all the registered user name and email"""
        users = User.query()
        strs = ""
        for user in users:
            strs += "(%s, %s)" % (user.name, user.email)
        return StringMessage(message = strs)


    
    @endpoints.method(
        request_message=endpoints.ResourceContainer(
        user_name=messages.StringField(1),),
        response_message=GameForms,
        path='games/user/{user_name}/active',
        name='get_user_games',
        http_method='GET')
    def get_user_games(self, request):
        """
        Return all of a user's active games.
        """
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name %s does not exist!' % request.user_name)
        
        active_games = Game.query(Game.user == user.key).filter(Game.game_over != True)
        
        return GameForms(items=[game.to_form("") for game in active_games])


    @endpoints.method(
        request_message=endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),),
        response_message=GameForm,
        path='/games/{urlsafe_game_key}/cancel', 
        name='cancel_game',
        http_method='POST')
    def cancel_game(self, request):
        """
        This endpoint allows users to cancel a game in progress.
        """
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found!')
        
        if game.is_canceled:
            return game.to_form("You have already canceled the game!")
        
        if game.game_over:
            return game.to_form("Game is already over!")

        if not game.game_over and not game.is_canceled:
            game.is_canceled = True
        
        game.put()
        return game.to_form("You just canceled the game!")
        

    @endpoints.method(
        request_message=endpoints.ResourceContainer(max_number=messages.IntegerField(1),),
        response_message=UserTotalScoreForms,
        path='/scores/total/top/{max_number}', 
        name='get_high_total_scores',
        http_method='GET')    
    def get_high_total_scores(self, request):
        """
        List the top high total score list, each item is (username, total_score). Total score is the sum of all the scores user earned.
        """
        max_number = int(request.max_number)

        scores = Score.query()
        score_dict = defaultdict(int)

        for score in scores:
            score_dict[score.user.get().name] += score.user_score_to_int()
        
        score_dict = dict(score_dict)
        score_list_sorted = sorted(score_dict.items(), key=operator.itemgetter(1), reverse=True)[0:max_number]

        forms = []
        for item in score_list_sorted:
            form = UserTotalScoreForm(user_name=item[0], total_score=item[1])
            forms.append(form)
        
        return UserTotalScoreForms(items=forms)
    
    @endpoints.method(
        request_message=endpoints.ResourceContainer(max_number=messages.IntegerField(1),),
        response_message=StringMessage,
        path='/rankings/top/{max_number}', 
        name="get_user_rankings",
        http_method="GET")
    def get_user_rankings(self, request):
        """
        The ranking is defined by the ratio of sum(score)/(2*game)
        """
        scores = Score.query()
        scores_list_dict = defaultdict(list)

        for score in scores:
            scores_list_dict[score.user.get().name].append(score.user_score_to_int())
        
        scores_list_dict = dict(scores_list_dict)
        
        performances_dict = {}
        for k, v in scores_list_dict.iteritems():
            performance = sum(v)/(2*len(v))
            performances_dict[k]=performance

        performances_list_sorted = sorted(performances_dict.items(), key=operator.itemgetter(1), reverse=True)[0: request.max_number]

        strs = json.dumps(performances_list_sorted)

        return StringMessage(message=strs)


    @endpoints.method(
                request_message=endpoints.ResourceContainer(
                urlsafe_game_key=messages.StringField(1),),
                response_message=StringMessage,
                path="games/{urlsafe_game_key}/history", 
                name="get_game_history",
                http_method="GET")
    def get_game_history(self, request):
        """
        The history of game, each move is record as (user_of_move, position_of_move)
        """
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found!')

        return StringMessage(message =game.history)


    @staticmethod
    def _cache_winning_chance():
        """Populates memcache with the average moves remaining of Games"""
        current_user = get_endpoints_current_user()
        scores = Score.query(Score.user.name == current_user.name).fetch()
        if scores:
            total = 2*len(scores)
            wins = sum([score.user_score_to_int() for score in scores])
            chance = wins/float(total)
            
            memcache.set(MEMCACHE_WINNING_CHANCE,
                         'The winning chance is {:.2f}'.format(chance))

    @endpoints.method(response_message=StringMessage,
                      path='games/winning_chance',
                      name='get_winning_chance',
                      http_method='GET')
    def get_winning_chance(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.get(MEMCACHE_WINNING_CHANCE) or '')



##add tic-tac-toe 
api = endpoints.api_server([TicTacToeApi])
