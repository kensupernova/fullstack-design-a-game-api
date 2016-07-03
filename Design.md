#Reflect on the design of the game

##What additional properties did you add to your models and why?  
The following properties added to the original 'Game' model:  
 - **user_tic**: It is used to store the tick user will use in the game  
 - **opponent**: Tic-tac-toe is a two-player game. User is the one who initiate the game. Opponnet is the other player  
 - **opponent_tick**: It is used to store the tick opponent will use in the game  
 - **game_over**: Whether the game has ended. Three ticks in a straight line 
 - **is_canceled**: Whether some one has canceled the game  
 - **board_state**: Store the state of the 3x3 game board  
 - **user_of_next_move**: Tic-tac-toe is played one after the other. It indicates who will make the next move in the game.   

The following properties added to the original 'Score' model:  
 - **opponent**: When a score is made, who versus who must be also created.   
 - **board_state**: Store the state of the board. How user and opponent end the fight.  
 - **result**: Whether tic-tac-toe end in "win", "lose", for "tie" for the user  
 - **user_score_to_int**: For user, the score has an digit representation for calculations of total_score and ranking   
 - **opponent_score_to_int**: Additionaly get the score in digit of the opponent
 
##What were some of the trade-offs or struggles you faced when implementing the new game logic?

1. I find it very hard to determine whether the game has ended after user make a new move. So I searched on the internet. After many hours of searching, I find [magic_square](http://mathworld.wolfram.com/MagicSquare.html) can be used to determine the state of tic-tac-toe game just like a piece of cake. 

2. Create Enum Property in 'Score' model is quite hard to do. Reading documents and code in github helps.

3. Understanding how Form work is also challenging for me. I spent time reading the documentation from GAE. It finally become clear to me. Form is extended from messages.Message. Message has differnt kinds of field.  It is a bit like serializer. And 'response_message' in 'endpoints.method' is an inherited 'Message' class model, 'request_message' is endpoints.ResourceContainer, which can be created from 'Message' class or message field.

