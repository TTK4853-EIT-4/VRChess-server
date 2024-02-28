import sqlite3

conn = sqlite3.connect('vrchess.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don't exist
def initialize_database():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sid TEXT,
            username TEXT UNIQUE,
            password TEXT,
            firstname TEXT,
            lastname TEXT
        )
    ''')

# Get user by id
def get_user_by_id(id):
    cursor.execute('SELECT * FROM users WHERE id = ?', (id,))
    return cursor.fetchone()

# Get user by username
def get_user_by_username(username):
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()

# Get user by username and password
def get_user_by_username_and_password(username, password):
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    return cursor.fetchone()

# Insert user
def insert_user(username, password, firstname, lastname):
    cursor.execute('INSERT INTO users (username, password, firstname, lastname) VALUES (?, ?, ?, ?)',
                   (username, password, firstname, lastname))
    conn.commit()

# Update user sid
def update_user_sid(username, sid):
    cursor.execute('UPDATE users SET sid = ? WHERE username = ?', (sid, username))
    conn.commit()