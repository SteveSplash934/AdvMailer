import sqlite3
import os
import configparser

class ConfigManager:
    def __init__(self, db_path='database.db', ini_path='config.ini'):
        self.db_path = db_path
        self.ini_path = ini_path
        self._init_db()

    def _init_db(self):
        db_exists = os.path.exists(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings 
                        (section TEXT, key TEXT, value TEXT, PRIMARY KEY (section, key))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS templates 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, filename TEXT, type TEXT)''')
        conn.commit()
        
        # If the database was just created, try to import from config.ini
        if not db_exists:
            self._import_from_ini()
        conn.close()

    def _import_from_ini(self):
        """Helper to migrate config.ini data into SQLite on first run."""
        if os.path.exists(self.ini_path):
            config = configparser.ConfigParser()
            config.read(self.ini_path)
            updates = []
            for section in config.sections():
                for key, value in config.items(section):
                    updates.append((section.upper(), key.lower(), value))
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany('INSERT OR REPLACE INTO settings VALUES (?, ?, ?)', updates)
        else:
            self._seed_defaults()

    def _seed_defaults(self):
        defaults = [
            ('SMTP', 'host', 'smtp.gmail.com'), ('SMTP', 'port', '587'),
            ('SMTP', 'username', ''), ('SMTP', 'password', ''),
            ('SENDER', 'name', 'Steve Splash'), ('SENDER', 'email', 'sender@example.com'),
            ('EMAIL_CONTENT', 'subject', 'Default Email Subject'),
            ('EMAIL_CONTENT', 'mode', 'html'), ('EMAIL_CONTENT', 'html_path', ''),
            ('EMAIL_CONTENT', 'plain_path', ''), ('SETTINGS', 'concurrency_limit', '5')
        ]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany('INSERT OR REPLACE INTO settings VALUES (?, ?, ?)', defaults)

    def get_all(self):
        data = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT section, key, value FROM settings')
            for section, key, value in cursor.fetchall():
                sec = section.upper()
                if sec not in data: data[sec] = {}
                data[sec][key.lower()] = value
        return data

    def update_from_dict(self, data):
        updates = []
        for section, keys in data.items():
            for key, value in keys.items():
                updates.append((section.upper(), key.lower(), str(value)))
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany('INSERT OR REPLACE INTO settings VALUES (?, ?, ?)', updates)

    def add_template(self, name, filename, t_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('INSERT INTO templates (name, filename, type) VALUES (?, ?, ?)', (name, filename, t_type))

    def get_templates(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name, filename, type FROM templates')
            return [{"name": r[0], "filename": r[1], "type": r[2]} for r in cursor.fetchall()]