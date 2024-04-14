from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room
import sqlite3 
import chess

app = Flask('__name__')

socketio = SocketIO(app)
db = sqlite3.connect('games.db')
cursor = db.cursor()
cursor.execute('SELECT * FROM my_games')
print(cursor.fetchall())
# cursor.execute('CREATE TABLE my_games (id TEXT NOT NULL, players INTEGER)')
cursor.close()
db.close()



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/createroom')
def createroom():
    return render_template('create_room.html')

@app.route('/joinroom')
def joinroom():
    return render_template('join_room.html')

@app.route('/join_room', methods=['POST'])
def my_join_room():
    roomname = request.form['roomname']
    db = sqlite3.connect('games.db')
    cursor = db.cursor()
    cursor.execute('SELECT * FROM my_games WHERE id=?', (roomname,))
    check = cursor.fetchone()
    
    if check == None:
        cursor.close()
        db.close()
        return render_template('join_room.html', warning="Room does not exist.")
    if check[1]>1:
        print(check)
        cursor.close()
        db.close()  
        return render_template('join_room.html', warning="Room is full.")
    cursor.execute('UPDATE my_games SET players = players+1 WHERE id=?', (roomname,))
    db.commit()
    cursor.close()
    db.close()
    board = chess.Board()
    board.apply_transform(chess.flip_horizontal)
    my_dict = {}
    for square, piece in board.piece_map().items():
        if piece.color:
            my_dict[square] = f'w{piece.symbol().lower()}'
        else:
            my_dict[square] = f'b{piece.symbol().lower()}'
    return render_template('chess_board.html', room=roomname, my_dict = my_dict, board_fen = board.fen(), turn = 'b')

    

@app.route('/create_room', methods=['POST'])
def create_room():
    roomname = request.form['roomname']
    db = sqlite3.connect('games.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM my_games WHERE id=?", (roomname,))
    check = cursor.fetchone()
    print(check)
    
    if check:
        cursor.close()
        db.close()
        return render_template('create_room.html', warning = 'A room already exists with that name')
    
    cursor.execute('INSERT INTO my_games VALUES (?, ?)', (roomname, 1))
    db.commit()
    cursor.close()
    db.close()
    
    board = chess.Board()
    board.apply_transform(chess.flip_vertical)
    my_dict = {}
    for square, piece in board.piece_map().items():
        if piece.color:
            my_dict[square] = f'w{piece.symbol().lower()}'
        else:
            my_dict[square] = f'b{piece.symbol().lower()}'
    
    return render_template('chess_board.html', room=roomname, my_dict = my_dict, board_fen = board.fen(), turn = 'w')

@socketio.on('join')
def join(data):
    room = data['room']
    join_room(room)
    
@socketio.on('message')
def handle_message(data):
    room = data['room']
    username = 'User'  # You can implement user authentication to get the actual username
    message = data['message']
    socketio.emit('message', {'username': username, 'message': message}, room=room)
    
@socketio.on('move')
def move(data):
    room = data['room']
    board_fen = data['boardfen']
    move = data['move']
    turn = data['turn']
    db = sqlite3.connect('games.db')
    cursor = db.cursor()
    cursor.execute('SELECT players FROM my_games WHERE id=(?)', (room,))
    players = cursor.fetchone()[0]
    cursor.close()
    db.close()
    if players<2:
        return 0
    board = chess.Board(fen = board_fen)
    if turn!='b':
        board.apply_transform(chess.flip_vertical)
        if not board.turn:
            return 0
    else:
        board.apply_transform(chess.flip_horizontal)
        if board.turn:
            return 0
    moves = [str(move) for move in list(board.legal_moves)]
    print(moves)
    if move in moves:
        print(move)
        board.push(chess.Move.from_uci(move))
        socketio.emit('movemiddle', {'boardfen': board.fen(), turn: turn}, room=room)
    else:
        socketio.emit('message', {'message': 'illegal move'}, room=room)

@socketio.on('movemade')
def movemade(data):
    board = chess.Board(fen=data['boardfen'])
    my_dict = {}
    turn = data['turn1']
    if not data['start']:
        if turn!='b':
                board.apply_transform(chess.flip_vertical)

        else:
                board.apply_transform(chess.flip_horizontal)
    for square, piece in board.piece_map().items():
        if piece.color:
            my_dict[square] = f'w{piece.symbol().lower()}'
        else:
            my_dict[square] = f'b{piece.symbol().lower()}'

        
    socketio.emit('update_board', {'my_dict': my_dict, 'boardfen': board.fen()}, room=request.sid)

if __name__ == "__main__":
    app.run()