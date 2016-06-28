"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb

from utils import get_endpoints_current_user


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email =ndb.StringProperty()

### CREATE USER - COMPUTER 
### COMPUTER WILL BE DEFAULT USER IN THE GAME
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
        
        form.message = message
        return form

    def end_game(self, end, winner):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(date=date.today(), winner=winner,
                      board_state=self.board_state)
        score.put()

    def judge_game(self):
    
        ## check whether free indices
        ## if not, a tie
        if int(self.board_state.find("-")) == -1:
            self.end_game(end=True, winner=None)
            return {
                "end": True,
                "winner": "TIE"
            }

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

        result = {}

        if positions_by_user_total == 15 and positions_by_opponent_total == 15:
            result["end"] = True
            result["winner"] = "TIE"

            self.end_game(end=True, winner=None)

        elif positions_by_user_total == 15:
            result["end"] = True
            result["winner"] = self.user_name

            self.end_game(end=True, winner=self.user)

        elif positions_by_opponent_total == 15:
            result["end"] = True
            result["winner"] = self.opponent_name

            self.end_game(end=True, winner=self.opponent)

        else:
            result["end"] = False
            result["winner"] = "NOONE"

        return result



class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    board_state = ndb.StringProperty(required=True)
    won = ndb.BooleanProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), board_state=self.board_state)

    @classmethod
    def from_form(cls, message):
        """Gets the current user and inserts a score.
        Args:
            message: A ScoreRequestMessage instance to be inserted.
        Returns:
            The Score entity that was inserted.
        """
        current_user = get_endpoints_current_user()
        entity = cls(winner=message.own, user=current_user, board_state=message.board_state)
        entity.put()
        return entity

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



class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)
    user_tic = messages.StringField(2, required=True, default="O")
    opponent_name = messages.StringField(3, required=True, default="computer")
    opponent_tic = messages.StringField(4, required=True, default="X")
    board_state = messages.StringField(5, required=True, default="---------")

    user_of_next_move = messages.StringField(6, required=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    ### position is an integer from 0 - 8 (inclusive)
    ### it will be transformed into the position on the 3X3 grid
    position = messages.IntegerField(1, required=True)
    user_of_move =  messages.StringField(2, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    board_state  =  messages.StringField(4, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


### tic-tac-toe board
class BoardMessage(messages.Message):
    """Board board_state"""
    board_state = messages.StringField(1, required=True)

# class ScoreRequestMessage(messages.Message):
#     """When request a single score"""
#     outcome = messages.StringField(1, required=True)

# class ScoreResponseMessage(messages.Message):
#     """Response score"""
#     id = messages.IntegerField(1)
#     outcome = messages.StringField(2)
#     played = messages.StringField(3)

# class ScoresListRequestMessage(messages.Message):
#     """When request scores list"""
#     limit = messages.IntegerField(1, default=10)
#     class Order(messages.Enum):
#         WHEN = 1
#         TEXT = 2
#     order = messages.EnumField(Order, 2, default=Order.WHEN)

# class ScoresListResponseMessage(messages.Message):
#     """Respond with a list stored scores"""
#     items = messages.MessageField(ScoreResponseMessage, 1, repeated=True)






















