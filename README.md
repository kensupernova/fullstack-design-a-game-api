#Full Stack Nanodegree Project － Design A Game

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
1.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
1.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.
 

##Game Description:
Tic-Tac-Toe is a simple game for two players. The default opponnet user is computer. It begins with 3X3 empty grid. Each players has to choose a symbol 'O' or 'X'. Two players one after another place 'O' or 'X' in the grid. Whoever succeeds in placing three marks in the straight line wins. Each move has to choose an empty indice in the grid. Many different Tic-Tac-Toe can be played by many different Users at any
given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`. 
## Steps to play the game:
1. create user with username and email address
2. start new game with username and opponnet name, and their ticks for playing (optional). Both must be registered.
3. easy move is new position in the free indice in the 3X3 grid.
4. whoever make three ticks in a line wins. It could also be a tie. 

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
 
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name, user_tic, opponent_name, opponent_tic, user_of_next_move
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. user_name or opponent_name provided must correspond to an
    existing user - will raise a NotFoundException if not. 
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
 
 - **get_users**
    - Path: 'users'
    - Method: GET
    - Parameters: None
    - Returns: Return all the registered users
    - Description: Each user is username and email. It is useful in testing.
 
 - **get_games**
    - Path: 'games'
    - Method: GET
    - Parameters: None
    - Returns: GameForms
    - Description: It can list all the games. urlsafe_game_key, game_over, is_canceld, board_state, and other information of all games is displayed.

    
 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, user_of_move, position_of_move
    - Returns: GameForm with new game state.
    - Description: Accepts a position in the free indice in the grid and returns the updated state of the game. If new position causes a game to end (win, tie, lose), two corresponding score entities will be created. One score for user and one score for opponent.
    
 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).
    
 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.
    
 - **get_winning_chance**
    - Path: 'games/winning_chance'
    - Method: GET
    - Parameters: None
    - Returns: StringMessage
    - Description: Gets the winning chance of the current user.

- **get_user_games**  
    - Path: 'games/user/{user_name}/active'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms
    - Description: list a User's active games.

- **cancel_game** 
	- Path: '/games/{urlsafe_game_key}/cancel'
    - Method: POST
    - Parameters: urlsafe_game_key
    - Returns: GameForm
    - Description: Cancel the game. is_canceled is set to 'True'.

- **get_high_total_scores**  
	- Path: '/scores/total/top/{max_number}'
    - Method: GET
    - Parameters: max_number
    - Returns: StringMessage
    - Description: List the top total_scores. Each is as (username, total_score). Total score is the sum of scores a use has earned.

- **get_user_rankings**  
   	- Path: '/rankings/top/{max_number}'
    - Method: GET
    - Parameters: max_number
    - Returns: StringMessage
    - Description: List the top ranking users. Each is as (username, performance) performance is defined as the ratio of total_score/(2*games). 


- **get_game_history**  
    - Path: 'games/{urlsafe_game_key}/history'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: StringMessage
    - Description: Display how the tic-tac-toe is played. List all the moves. Each move is (username, position)


##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with Users model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, board_state,
    user_of_next_move, game_over, message, user_name, user_tic, opponent_name, opponent_tic).
 - **NewGameForm**
    - Used to create a new game (user_name, user_tic, opponent_name, opponent_tic, user_of_next_move)
 - **MakeMoveForm**
    - Inbound make move form (position).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, result, board_state).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
 - **UserTotalScoreForm**
    - Represent the total scores of a user (user_name, total_score)
 - **UserTotalScoreForms**
    - Multiple UserTotalScoreForm container