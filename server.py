from ast import dump
from functools import wraps
import os
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room
from flask import Flask, make_response, render_template, request, redirect, url_for
from user import User
from GameRoom import GameRoom, GameRoomJSONEncoder, PlayerMode , SideColor , GameStatus
import datetime
import hashlib
import json
import jwt
import database.database as database
import argparse

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f9bf78b9a18ce6d46a0cd2b0b86df9da'
app.config['SESSION_TYPE'] = 'filesystem'
socketio = SocketIO(app, manage_session=False)

# Stop http logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Initialize the database
database.initialize_database()

connected_users = {}
game_rooms = {}

@app.route('/')
def index():
    user = get_logged_in_user()
    return render_template('index.html', title = "VRChess - Home", user = user)

@app.route('/login')
def login():
    # Get AuthToken cookie
    token = request.cookies.get('AuthToken')
    if token:
        user_id = decode_auth_token(token)
        if user_id != 0:
            user_data = database.get_user_by_id(user_id)
            if user_data:
                return redirect(url_for('index'))
    
    return render_template('login.html', title = "VRChess - Login")

@app.route('/signup')
def signup():
    # If the user is already logged in, redirect to home
    user = get_logged_in_user()
    if user:
        return redirect(url_for('index'))
    return render_template('signup.html', title = "VRChess - Sign Up")

# TODO: Add validation for the form data
@app.route('/signup', methods=['POST'])
def signup_post():
    username = request.form.get('username')
    password = request.form.get('password')
    password_hashed = hashlib.md5(password.encode()).hexdigest()
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')

    existing_user = database.get_user_by_username(username)

    if existing_user:
        return render_template('signup.html', title="VRChess - Sign Up", error_message="Username already exists")
    
    database.insert_user(username, password_hashed, firstname, lastname)

    return redirect(url_for('index'))

# TODO: Add validation for the form data
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    password_hashed = hashlib.md5(password.encode()).hexdigest()

    user_data = database.get_user_by_username_and_password(username, password_hashed)

    if user_data:
        user = User(*user_data)

         # Create a JWT token
        token = create_jwt_token(user.id)

        # Return the token in the response header
        response = make_response(redirect(url_for('index')))
        #response.headers['Authorization'] = f'Bearer {token}'

        # Set httpOnly cookie
        response.set_cookie('AuthToken', token, httponly=True)

        return response
    else:
        return render_template('login.html', title = "VRChess - Login", error_message="Invalid username or password")

@app.route('/logout')
def logout():
    # Remove AuthRoken cookie
    response = make_response(redirect(url_for('index')))
    response.set_cookie('AuthToken', '', expires=0, httponly=True)
    return response

@app.route('/profile/<username>')
def profile(username):
    user_data = database.get_user_by_username(username)

    if user_data:
        user = User(*user_data)
        return render_template('profile.html', title = "VRChess - " + user.username, user = user)
    else:
        return render_template('profile.html', title = "VRChess - User not found", error_message=f"User {username} not found")

@app.route('/rooms')
def rooms():
    # Get logged in user
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('room-list.html', title = "VRChess - Rooms", user = user)

@app.route('/createroom')
def create_room():
    user = get_logged_in_user()
    room = GameRoom(user)
    socketio.emit('room_created', {'room_id': str(room.room_id), 'room_owner': user.username})
    # return the room view
    return render_template('room.html', title = "VRChess - Room", room = room)

@app.route('/room/<uuid:room_id>')
def room(room_id):
    user = get_logged_in_user()
    if not user:
        return redirect(url_for('login'))
    # Fetch room details based on room_id
    room = game_rooms.get(str(room_id))
    if room :
        if room.room_owner.username == user.username or (room.room_opponent != None and room.room_opponent.username == user.username) or \
            any(observer.id == user.id for observer in room.observers) :
                return render_template('room.html', title="VRChess - Room", user=user , room = room)
        return render_template('room-list.html', title = "VRChess - Rooms", user = user , error_message=f"You are not this room")
    else :
        return render_template('room-list.html', title = "VRChess - Rooms", user = user , error_message=f"Room not found")



# Filter for checking if the user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('AuthToken')
        if not token:
            return emit('unauthorized', {'message': 'User not authenticated'})
        user_id = decode_auth_token(token)
        if user_id == 0:
            return emit('unauthorized', {'message': 'User not authenticated'})
        return f(*args, **kwargs)
    return decorated_function


# Filter for not logged in users
def not_logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('AuthToken')
        if token:
            return emit('unauthorized', {'message': 'User already authenticated'})
        return f(*args, **kwargs)
    return decorated_function


@socketio.on('connect')
def handle_connect():
    user = get_logged_in_user()
    if user:
        database.update_user_sid(user.username, request.sid)
        print(f"Client connected: {request.sid}, Authenticated: {user.username}")
    else:
        print(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    user = get_logged_in_user()
    if user:
        database.update_user_sid(user.username, None)
        print(f"User disconnected: {user.username} {request.sid}")


# On register event with ACK response from server
# TODO: Add validation for username and password
@socketio.on('register')
@not_logged_in
def handle_register(data):
    username = data['username']
    password = data['password']
    password_hashed = hashlib.md5(password.encode()).hexdigest()
    firstname = data['firstname']
    lastname = data['lastname']

    existing_user = database.get_user_by_username(username)

    if existing_user:
        return {'status': 'error', 'message': 'Username already exists'}
    
    database.insert_user(username, password_hashed, firstname, lastname)

    return {'status': 'success', 'message': 'User registered successfully'}


# TODO: Add validation for the form data
@socketio.on('login')
@not_logged_in
def handle_login(data):
    username = data['username']
    password = data['password']
    password_hashed = hashlib.md5(password.encode()).hexdigest()
    user_data = database.get_user_by_username_and_password(username, password_hashed)

    if user_data:
        user = User(*user_data)
        user.sid = request.sid

         # Create a JWT token
        token = create_jwt_token(user.id)

        # Update the sid in db
        database.update_user_sid(username, request.sid)

        emit('authenticated', {'token': token})

        return {'status': 'success', 'message': 'Logged in successfully.', 'data': user.serialize()}
    else:
        return {'status': 'error', 'message': 'Invalid username or password'}


@socketio.on('create_room')
@login_required
def create_room(data):
    user = get_logged_in_user()
    player_mode = data.get('player_mode')

    if not user:
        return {'status': 'error', 'message': 'User not authenticated'}

    # Check if the user is already in a room or has a room
    for room_loop in game_rooms.values():
        if room_loop.room_owner.username == user.username or (room_loop.room_opponent != None and room_loop.room_opponent.username == user.username) or \
            any(observer.id == user.id for observer in room_loop.observers) :
            return {'status': 'error', 'message': f"Your are already in a room {room_loop.room_id}"}
    
    # Creating a new room
    room = GameRoom(user)
    room.set_player_mode(player_mode)
    side = data.get('side')
    
    # change side if it's black ( white by default)
    if side == 'black':
        room.room_owner_side = SideColor.BLACK

    # if player mode is PlayerMode.BOARD_TWO_PLAYER, add the opponent to the room
    if player_mode == PlayerMode.BOARD_TWO_PLAYER.value:
        print('Create room:', data)
        opponent_username = data.get('opponent')
        opponent_user = database.get_user_by_username(opponent_username)
        if opponent_user is None:
            return {'status': 'error', 'message': f"User {opponent_username} not found"}
        
        opponent_user = User(*opponent_user)
        
        # If opponent is already in a room or has a room
        for room_loop in game_rooms.values():
            if room_loop.room_owner.username == opponent_user.username or (room_loop.room_opponent != None and room_loop.room_opponent.username == opponent_user.username) or \
                any(observer.id == opponent_user.id for observer in room_loop.observers) :
                return {'status': 'error', 'message': f"User {opponent_user.username} is already in a room {room_loop.room_id}"}
            
        # Add opponent to the room
        room.add_opponent(opponent_user)
        room.start_game()

    game_rooms[room.room_id] = room

    emit('room_created', room.serialize(), broadcast=True)
    print(f"Room created: {room.room_id} by {user.username}")
    return  {'status': 'success', 'message': 'Room created successfully', 'data': room.serialize()}


# Get all rooms
@socketio.on('get_all_rooms')
def get_all_rooms():
    json_string = json.dumps([ob for ob in game_rooms.values()], cls = GameRoomJSONEncoder)
    return json_string


# Delete room
@socketio.on('delete_room')
@login_required
def delete_room(data):
    user = get_logged_in_user()
    room_id = data.get('room_id')
    if room_id in game_rooms:
        room = game_rooms[room_id]
        if room.room_owner.username == user.username:
            del game_rooms[room_id]

            # Removes any users that are in the given room and then deletes the room from the server
            close_room(room_id)
            emit('room_deleted', {'room_id': room_id}, broadcast = True)
            return {'status': 'success', 'message': f"Room {room_id} deleted successfully"}
        else:
            return {'status': 'error', 'message': f"You are not the owner of the room {room_id}"}


@socketio.on('test')
def handle_test(data):
    # get logged in user
    user = get_logged_in_user()
    print('Test:', data, user)

    # Subscribe the connected client to the socket room 'test-123'
    room = 'test-123'
    join_room(room, sid=request.sid)

    # Emit to socket room 'test-123' only
    emit('hello', {'message': 'Test message'}, room='test-123')


@socketio.on('join_game')
@login_required
def join_game(data):
    room_id = data.get('room_id')
    user = get_logged_in_user()

    # Check if user is already in a room or has a room
    for room in game_rooms.values():
        if room.room_owner.username == user.username or (room.room_opponent != None and room.room_opponent.username == user.username) or \
            any(observer.id == user.id for observer in room.observers) :
            return {'status': 'error', 'message': f"Your are already in a room {room.room_id}"}

    # Check if the room exists
    if room_id in game_rooms: 
        room = game_rooms[room_id]
        
        # Check if the room is already full
        if room.room_opponent is not None:
            return {'status': 'error', 'message': 'Room is already full'}

        # Add the user as the opponent in the room and start the game
        room.add_opponent(user)
        room.start_game()

        # Update the game_rooms dictionary with the modified room object
        game_rooms[room_id] = room
         
        # Emit event to notify ALL users for the room update
        socketio.emit('room_updated',  room.serialize())

        # Emit event to notify only the room participants for the updated room
        socketio.emit('room_updated_', room.serialize(), room=room_id)

        return {'status': 'success', 'message': 'Joined room successfully'} 

    else:
        return {'status': 'error', 'message': 'Room does not exist'}
    

@socketio.on('observe_game')
@login_required
def observe_game(data):
    room_id = data.get('room_id')
    user = get_logged_in_user()

    # Check if user is already in a room or has a room
    for room in game_rooms.values():
        if room.room_owner.username == user.username or (room.room_opponent != None and room.room_opponent.username == user.username) or \
            any(observer.id == user.id for observer in room.observers) :
            return {'status': 'error', 'message': f"Your are already in a room {room.room_id}"}

    # Check if the room exists
    if room_id in game_rooms: 
        room = game_rooms[room_id]
        # Add the user as observer in the room
        if room.add_observer(user) :
            # Update the game_rooms dictionary with the modified room object
            game_rooms[room_id] = room
            # Emit event to notify ALL users for the room update (using for updating the room list in the client side)
            socketio.emit('room_updated', room.serialize())

            socketio.emit('room_updated_', room.serialize(), room=room_id)
            return {'status': 'success', 'message': f'Joined room as observer successfully'}
        else :
            return {'status': 'error', 'message': f'You are already observing this room'}
    else:
        return {'status': 'error', 'message': 'Room does not exist'}


# On subscribe to socket room event
@socketio.on('subscribe_to_room')
@login_required
def subscribe_to_room(data):
    room_id = data.get('room_id')
    user = get_logged_in_user()
    room = game_rooms.get(room_id)
    if room:
        if room.room_owner.username == user.username or (room.room_opponent != None and room.room_opponent.username == user.username) or \
            any(observer.id == user.id for observer in room.observers) :
            join_room(room_id, sid=request.sid)
            return {'status': 'success', 'message': f'Subscribed to room {room_id}'}
        else:
            return {'status': 'error', 'message': f"You are not in this room {room_id}"}
    else:
        return {'status': 'error', 'message': f"Room {room_id} does not exist"}


# On piece_move event with move validation
@socketio.on('piece_move')
@login_required
def piece_move(data):
    room_id = data.get('room_id')
    move = data.get('move') # format: { "source": "c7", "target": "c5", "piece": "bP" , "promotedPiece" : None}
    user = get_logged_in_user()
    room = game_rooms.get(room_id)
    if room:
        if room.room_owner.username == user.username or (room.room_opponent != None and room.room_opponent.username == user.username) :
            if room.game_status == GameStatus.WAITING:
                return {'status': 'error', 'message': "Game didn't start yet. Please wait for opponent"}
            elif room.game_status == GameStatus.ENDED :
                return {'status': 'error', 'message': "Game ended. Please start a new room to play again"}

            import chess
            if  move['promotedPiece'] is None:
                Nf3 = chess.Move.from_uci(move['source'] + move['target'] )
            else :
                Nf3 = chess.Move.from_uci(move['source'] + move['target']+ move['promotedPiece'] )

            # check if the move is valid
            if Nf3 not in room.game.legal_moves:
                return {'status': 'error', 'message': f"{Nf3} is not a legal move."}
            
            room.game.push(Nf3)
            print("\n")
            print(room.game)
            

            # update the game in list
            game_rooms[room_id] = room

            outcome = room.game.outcome()
            if outcome is not None:
                termination = outcome.termination
                winner = outcome.winner
                game_rooms.pop(room_id)
                
                if termination == chess.Termination.CHECKMATE:
                    if winner == chess.WHITE:
                        room.end_game(SideColor.WHITE)
                        print("Game over: White wins by checkmate!")
                    else:
                        room.end_game(SideColor.BLACK)
                        print("Game over: Black wins by checkmate!")
                elif termination == chess.Termination.STALEMATE:
                    room.end_game()
                    print("Game ended in stalemate!")
                elif termination == chess.Termination.INSUFFICIENT_MATERIAL:
                    room.end_game()
                    print("Game ended due to insufficient material!")
                elif termination == chess.Termination.FIVEFOLD_REPETITION:
                    room.end_game()
                    print("Game ended due to fivefold repetition!")
                elif termination == chess.Termination.FIFTY_MOVES:
                    room.end_game()
                    print("Game ended due to fifty moves rule!")
                elif termination == chess.Termination.THREEFOLD_REPETITION:
                    room.end_game()
                    print("Game ended due to threefold repetition!")   
                # Emit event to notify only the room participants for the end of the room
                socketio.emit('room_updated_', room.serialize(), room=room_id) 

            # return data: {move: move, fen: room.game.fen()}
            return_data = {'move': move, 'fen': room.game.fen()}
            emit('piece_moved_', return_data, room=room_id, skip_sid=request.sid)
            return {'status': 'success', 'message': f'Piece moved successfully', 'data': room.game.fen()}
        else:
            return {'status': 'error', 'message': f"You are not playing in this room {room_id}"}
    else:
        return {'status': 'error', 'message': f"Room {room_id} does not exist"}


# On piece_move_notify event which do not validate the move but only notify the move to the room participants
@socketio.on('piece_move_notify')
@login_required
def piece_move_notify(data):
    # data format: { "room_id": "xxx", "move": { "fen": "xxx" } }
    room_id = data.get('room_id')
    move = data.get('move') # format: { "fen": "xxx" }
    user = get_logged_in_user()
    room = game_rooms.get(room_id)
    if room:
        if room.room_owner.username == user.username or (room.room_opponent != None and room.room_opponent.username == user.username) :
            emit('piece_moved_', move, room=room_id, skip_sid=request.sid)
            return {'status': 'success', 'message': f'Piece moved successfully'}
        else:
            return {'status': 'error', 'message': f"You are not playing in this room {room_id}"}
    else:
        return {'status': 'error', 'message': f"Room {room_id} does not exist"}


# get the connected user
@socketio.on('get_my_user')
@login_required
def get_my_user():
    user = get_logged_in_user()
    return user.serialize()


@socketio.on('try_join_game')
def try_join_game(data):
    token = data['AuthToken']
    for room in game_rooms.values():
        if room.room_opponent is None:
            print('Joining game:', room.room_id)
            join_game({'room_id': room.room_id})
            return
    print('No available games. Creating a new one')
    create_room(data={'read_only': False, 'token': token})


# Create JWT token
def create_jwt_token(user_id):
    # Read the secret key from file
    with open(os.path.dirname(__file__) + '/key.txt', 'r') as file:
        key = file.read()
    # Create a JWT token
    token = jwt.encode({
        'user_id': user_id, 
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, key = key, algorithm='HS256')
    return token

# JWT Token Decode
def decode_auth_token(auth_token):
    try:
        # Read the secret key from file
        with open(os.path.dirname(__file__) + '/key.txt', 'r') as file:
            key = file.read()
        #payload = jwt.decode(auth_token, key)
        payload = jwt.decode(auth_token, key = key, verify=True, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return 0
    except jwt.InvalidTokenError:
        return 0
    
# Get logged in user
def get_logged_in_user():
    token = request.cookies.get('AuthToken')
    if token:
        user_id = decode_auth_token(token)
        if user_id != 0:
            user_data = database.get_user_by_id(user_id)
            if user_data:
                return User(*user_data)
    return None

# Add argument parser
parser = argparse.ArgumentParser(description='Run the Flask application.')
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
args = parser.parse_args()

if __name__ == '__main__':
    if args.debug:
        socketio.run(app, host="0.0.0.0", debug=True, allow_unsafe_werkzeug=True)
    else:
        socketio.run(app, host="0.0.0.0", allow_unsafe_werkzeug=True)
