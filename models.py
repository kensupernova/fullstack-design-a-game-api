"""models.py - This file contains the class definitions for the Datastore
entities and Endpoints used by the Game. It inlcudes User, Game, Score. And it also
include message model GameForm, NewGameForm, MessageForm, ScoreForm, ScoreForms. """
import re
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop

from utils import get_endpoints_current_user

class Result(messages.Enum):
    LOSE = 0
    TIE = 1
    WIN = 2


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()

### CREATE USER - COMPUTER 
### COMPUTER WILL BE DEFAULT USER IN THE GAME
if not User.query(User.name == "computer").get():
    computer = User(name="computer")
    computer.put()

class Game(ndb.Model):
    """Game object"""
    user = ndb.KeyProperty(required=True, kind='User')
    user_tic = ndb.StringProperty(required=True, default="O")

    opponent = ndb.KeyProperty(required=True, kind='User')
    opponent_tic = ndb.StringProperty(required=True, default="X")
    
    ## game
    game_over = ndb.BooleanProperty(required=True, default=False)
    board_state = ndb.StringProperty(required=True)
    user_of_next_move = ndb.KeyProperty(required=True, kind='User')
    is_canceled = ndb.BooleanProperty(required=False, default=False)

    ## history will be saved as string with move (user_of_move, position_of_move)
    history = ndb.StringProperty(required=True, default="")
    
    ### tic tac toe game board state
    ### 3X3 = 9 characters
    """ For example
    -O-
    -XO
    --X
    """

    

    @classmethod
    def new_game(cls, user, user_tic, opponent, opponent_tic, user_of_next_move):
        """Creates and returns a new game"""
        ### default b user is a computer
        game = Game(user=user,
                    user_tic=user_tic,
                    opponent=opponent, 
                    opponent_tic=opponent_tic, 
                    game_over=False,
                    board_state="---------", 
                    user_of_next_move = user_of_next_move)
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.opponent_name = self.opponent.get().name
        
        form.board_state = self.board_state
        form.game_over = self.game_over
        form.user_of_next_move = self.user_of_next_move.get().name

        form.is_canceled = self.is_canceled
        
        form.message = message
        return form

    def end_game(self, end, result):
        """Ends the game"""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'

        score = Score(user=self.user, opponent=self.opponent, date=date.today(), 
                      board_state=self.board_state, result=result)
        score.put()

        ## move from either player will end the game, and generate two scores
        ## one for user, one for opponent
        if result ==  Result.WIN:
            opponent_result = Result.LOSE
        elif result == Result.LOSE:
            opponent_result = Result.WIN
        else:
            opponent_result = result

        oppo_score = Score(user=self.opponent, opponent=self.user, date=date.today(), 
                      board_state=self.board_state, result=opponent_result)
        oppo_score.put()

    def judge_game(self):
        ## return whether ended, who is winner, result of game
        result = {}

        ## check whether free indices
        ## if not, a tie
        if int(self.board_state.find("-")) == -1:
            self.end_game(end=True, result=Result.TIE)  
            result["end"] = True
            result["winner"] = "BOTH"
            result["result"] = "TIE"

        positions_by_user = [match.start()
                                for match in re.finditer(self.user_tic, self.board_state)]

        positions_by_opponent = [match.start()
                                for match in re.finditer(self.opponent_tic, self.board_state)]

        ### used to determine whether someone has win by add the digits in the positions
        ### if equals 15, yes
        ### more information: http://mathworld.wolfram.com/MagicSquare.html

        magic_square = [8, 1, 6, 3, 5, 7, 4, 9, 2]

        positions_by_user_total = 0
        for i in positions_by_user:
            positions_by_user_total += magic_square[i]

        positions_by_opponent_total = 0
        for i in positions_by_opponent:
            positions_by_opponent_total += magic_square[i]

        # positions_by_user_total =reduce(lambda a, b: magic_square[a]+magic_square[b], positions_by_user)

        

        if positions_by_user_total == 15 and positions_by_opponent_total == 15:
            result["end"] = True
            result["winner"] = "BOTH"
            result["result"] = "TIE"

            self.end_game(end=True, result=Result.Tie)

        elif positions_by_user_total == 15 and positions_by_opponent_total != 15:
            result["end"] = True
            result["winner"] = self.user.get().name
            result["result"] = "WIN"
            self.end_game(end=True, result=Result.WIN)

        elif positions_by_opponent_total == 15 and positions_by_user_total != 15 :
            result["end"] = True
            result["winner"] = self.opponent_name
            result["result"] = "LOSE"


            self.end_game(end=True, result=Result.LOSE)

        else:
            result["end"] = False

        return result




class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    opponent = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    board_state = ndb.StringProperty(required=True)
    # E
    result = msgprop.EnumProperty(Result, required=True)

    def to_form(self):
        if self.result == Result.WIN:
            result = "WIN"
        elif self.result == Result.TIE:
            result = "TIE"
        else:
            result = "LOSE"
        if not self.opponent:
            return ScoreForm(user_name=self.user.get().name, result=result,
                         date=str(self.date), board_state=self.board_state, opponent_name="computer")
        return ScoreForm(user_name=self.user.get().name, result=result,
                         date=str(self.date), board_state=self.board_state, opponent_name=self.opponent.get().name)


    @classmethod
    def from_form(cls, message):
        """Gets the current user and inserts a score.
        Args:
            message: A ScoreRequestMessage instance to be inserted.
        Returns:
            The Score entity that was inserted.
        """
        current_user = get_endpoints_current_user().key
        opponent = User.query(User.name == message.opponent_name)
        if message.result == 'WIN':
            result = Result.WIN
        elif message.result == 'TIE':
            result = Result.TIE
        else:
            result = Result.LOSE

        entity = cls(user=current_user, opponent=opponent,
            board_state=message.board_state, result=result,
            )
        entity.put()
        return entity

    def user_score_to_int(self):
        if self.result == Result.WIN:
            result = 2
        elif self.result == Result.TIE:
            result = 1
        else:
            result = 0
        return result

    def opponent_score_to_int(self):
        if self.result == Result.WIN:
            result = 0
        elif self.result == Result.TIE:
            result = 1
        else:
            result = 2
        return result

    ### the user of the score
    @classmethod
    def query_current_user(cls):
        """Creates a query for the scores of the current user.
        Returns:
            An ndb.Query object bound to the current user. This can be used
            to filter for other properties or order by them.
        """
        current_user = get_endpoints_current_user()
        return cls.query(cls.user == current_user)

    @property
    def timestamp(self):
        return self.date.strftime('%b %d, %Y %I:%M:%S %p')

class GameForm(messages.Message):
    """GameForm for outbound game board_state information"""
    urlsafe_key = messages.StringField(1, required=True)
    
    board_state = messages.StringField(2, required=True)
    user_of_next_move = messages.StringField(3, required=True)
    game_over = messages.BooleanField(4, required=True)

    message = messages.StringField(5, required=True)
    
    user_name = messages.StringField(6, required=True)
    user_tic = messages.StringField(7, required=True, default="O")
    opponent_name = messages.StringField(8, required=True)
    opponent_tic = messages.StringField(9, required=True, default="X")

    is_canceled = messages.BooleanField(10, required=True)




class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    user_tic = messages.StringField(2, required=True, default="O")
    opponent_name = messages.StringField(3, required=True, default="computer")
    opponent_tic = messages.StringField(4, required=True, default="X")


class MakeMoveForm(messages.Message):
    """
    Used to make a move in an existing game. 
    position is an integer from 0 - 8 (inclusive)
    it will be transformed into the position on the 3X3 grid
    """
    user_of_move =  messages.StringField(1, required=True)
    position = messages.IntegerField(2, required=True)
    

class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    result = messages.StringField(3, required=True)
    board_state  =  messages.StringField(4, required=True)
    opponent_name = messages.StringField(5, required=False, default="computer")


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)

class GameForms(messages.Message):
    items = messages.MessageField(GameForm, 1, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)

### tic-tac-toe board
class BoardMessage(messages.Message):
    """Board board_state"""
    board_state = messages.StringField(1, required=True)

class UserTotalScoreForm(messages.Message):
    """It will list username, the total scores of all the played games"""
    user_name = messages.StringField(1, required=True)
    total_score = messages.IntegerField(2, required=True)

class UserTotalScoreForms(messages.Message):
    """Many UserTotalScoreForm"""
    items=messages.MessageField(UserTotalScoreForm, 1, repeated=True)

























