import sqlite3
import threading

conn = sqlite3.connect('vrchess.db', check_same_thread=False)
cursor = conn.cursor()
lock = threading.Lock()

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

def queryLock(func):
    def wrapper(*args, **kwargs):
        try:
            lock.acquire(True)
            return func(*args, **kwargs)
        finally:
            lock.release()
    return wrapper

def execute_query(query, params):
    cursor.execute(query, params)
    conn.commit()

# Get user by id
@queryLock
def get_user_by_id(id):
    execute_query('SELECT * FROM users WHERE id = ?', (id,))
    return cursor.fetchone()

# Get user by username
@queryLock
def get_user_by_username(username):
    execute_query('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()

# Get user by username and password
@queryLock
def get_user_by_username_and_password(username, password):
    execute_query('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    return cursor.fetchone()

# Insert user
@queryLock
def insert_user(username, password, firstname, lastname):
    execute_query('INSERT INTO users (username, password, firstname, lastname) VALUES (?, ?, ?, ?)',
                       (username, password, firstname, lastname))

# Update user sid
@queryLock
def update_user_sid(username, sid):
    execute_query('UPDATE users SET sid = ? WHERE username = ?', (sid, username))