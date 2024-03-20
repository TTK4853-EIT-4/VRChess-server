# VRChess Server Side

## Getting started

### Flask server

The server code is located in the `flask_server` directory. To run the server, you need to install the dependencies in `requirements.txt` and run `python3 server.py`. The server will be running on `localhost:5000`. Alternatively, you can run the server by executing the batch file `run.bat` (Windows).
The batch file tries to activate the virtual environment `..\..\myenv` and then runs the server. If you are not using Windows, you can activate the virtual environment manually by running for example `source myenv/bin/activate` and then run the server with `python3 server.py`.

#### Virtual environment setup

<https://docs.python.org/3/library/venv.html>

### Example .NET client

The example client project and code are located in the `test_dotnet_client` directory. To run the client, you need to install Visual Studio with .NET 8

## Server-Client Communication

### Server Side

#### Event Listening

The socketIO server listens for incoming connections on the port 5000. The server listens for the following events:

| ID   | Name              | Description                                                    | Request Data                                                                                         | Return                                                                                           | Emit                                | LoggedIn       |
|------|-------------------|----------------------------------------------------------------|------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|-------------------------------------|----------------|
| SL1  | connect           | When a client connects to the server                           |                                                                                                      |                                                                                                  |                                     |                |
| SL2  | disconnect        | When a client disconnects from the   server                    |                                                                                                      |                                                                                                  |                                     |                |
| SL3  | test              | Used for test purposes                                         |                                                                                                      |                                                                                                  |                                     |                |
| SL4  | register          | When a client sends a register request                         | { "username": "user1", "password":   "password", "firstname": "John",   "lastname": "Doe" }          | {'status': 'success\|error',   'message': 'User registered successfully'}                        |                                     | @not_logged_in |
| SL5  | login             | When a client sends a login request                            | { "username": "user1", "password":   "password1" }                                                   | {'status': 'success\|error', 'message': 'Logged in successfully.', 'data':   user.serialize()}   | authenticated                       | @not_logged_in |
| SL6  | create_room       | When a client sends a create room request                      | { "player_mode": "1 \| 2", "opponent":   "opponent_username" }                                       | {'status': 'success\|error', 'message': 'Room created successfully',   'data': room.serialize()} | room_created(Br)                    | Yes            |
| SL7  | delete_room       | When a client sends a delete room request                      | { "room_id": "###" }                                                                                 | { "status": "success\|error", "message":   "Room deleted successfully" }                         | room_deleted(Br)                    | Yes            |
| SL8  | get_all_rooms     | When a client wants to receive a   list with all created rooms |                                                                                                      | list with all rooms serialized                                                                   |                                     |                |
| SL9  | join_game         | When a client wants to join a room as an opponent player       | { "room_id": "###" }                                                                                 | {"success\|error","msg"}                                                                         | room_updated(Br), room_updated_(Mu) | Yes            |
| SL10 | observe_game      | When a client wants to observe a game                          | { "room_id": "###" }                                                                                 | { "status": "success\|error", "message":   "Joined room as observer successfully" }              | room_updated(Br), room_updated_(Mu) | Yes            |
| SL11 | subscribe_to_room | When a client wants to subscribe to a specific room            | { "room_id": "###" }                                                                                 | { "status":   "success\|error", "message": "Subscribed to room   ###" }                          |                                     | Yes            |
| SL12 | piece_move        | When a client want to move a piece                             | { "room_id": "###", "color":   "1\|2", "move": { "source": "c7",   "target": "c5", "piece": "bP" } } | { "status": "success\|error", "message":   "Piece moved successfully", "data": "FEN" }           | piece_moved_(Mu)                    | Yes            |
| SL13 | get_my_user       | When the client wants to receive his   user data               |                                                                                                      | Serialized User obj                                                                              |                                     | Yes            |


#### Event Emitting

The server emits the following events:

| ID  | Name          | Description                                                                           | Send Data                                                                       | Send To                     |
|-----|---------------|---------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|-----------------------------|
| SE1 | room_created  | Notify clients for new room   creation                                                | Serialized Room Obj                                                             | Broadcast                   |
| SE2 | room_deleted  | Notify clients for a room delete                                                      | {"room_id": room_id}                                                            | Broadcast                   |
| SE3 | room_updated  | Notify all clients that a   specific room is updated (opponent/observer joined etc..) | Serialized Room Obj                                                             | Broadcast                   |
| SE4 | room_updated_ | Notify room's clients that the   room is updated (opponent/observer joined etc..)     | Serialized Room Obj                                                             | Multicast to room's clients |
| SE5 | piece_moved_  | Notify room's clients that a   piece is moved                                         | { "move": {   "source": "c7", "target": "c5",   "piece": "bP" }, "fen": "FEN" } | Multicast to room's clients |

### Client Side

#### Event Emitting

The client emits the following events:

#### Event Listening

The client listens for the following events: