from datetime import datetime

class User:
    def __init__(self, id, sid, username, password, firstname, lastname):
        self.id = id
        self.sid = sid
        self.username = username
        self.password = password
        self.firstname = firstname
        self.lastname = lastname
        self.last_online = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.friends = []
        self.games = []

    def update_last_online(self):
        self.last_online = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def serialize(self):
        return {
            'id': self.id,
            'username': self.username,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'last_online': self.last_online
        }