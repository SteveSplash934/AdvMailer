import sqlite3
import os
import json
import configparser
from datetime import datetime

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
        cursor.execute('''CREATE TABLE IF NOT EXISTS job_history 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, subject TEXT, sent INTEGER, failed INTEGER, status TEXT)''')
        conn.commit()
        
        if not db_exists:
            self._import_from_ini()
        conn.close()

    def _import_from_ini(self):
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
            ('EMAIL_CONTENT', 'plain_path', ''), ('EMAIL_CONTENT', 'selected_attachments', '[]'),
            ('SETTINGS', 'concurrency_limit', '5')
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

    def reset_config(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM settings')
        if os.path.exists(self.ini_path):
            self._import_from_ini()
        else:
            self._seed_defaults()

    def wipe_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM settings')
            conn.execute('DELETE FROM templates')
            conn.execute('DELETE FROM job_history')
        if os.path.exists(self.ini_path):
            self._import_from_ini()
        else:
            self._seed_defaults()

    def get_selected_attachments(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE section = 'EMAIL_CONTENT' AND key = 'selected_attachments'")
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except:
                    return [x.strip() for x in row[0].split(',') if x.strip()]
            return []

    def save_selected_attachments(self, file_list):
        val = json.dumps(file_list)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO settings (section, key, value) VALUES ('EMAIL_CONTENT', 'selected_attachments', ?)", (val,))

    def add_template(self, name, filename, t_type):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('INSERT INTO templates (name, filename, type) VALUES (?, ?, ?)', (name, filename, t_type))

    def delete_template(self, filename):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM templates WHERE filename = ?', (filename,))

    def get_templates(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name, filename, type FROM templates')
            return [{"name": r[0], "filename": r[1], "type": r[2]} for r in cursor.fetchall()]

    def add_job(self, subject):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('INSERT INTO job_history (date, subject, sent, failed, status) VALUES (?, ?, 0, 0, "Running")', (date_str, subject))
            return cursor.lastrowid

    def update_job(self, job_id, sent, failed, status):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE job_history SET sent = ?, failed = ?, status = ? WHERE id = ?', (sent, failed, status, job_id))

    def get_history(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT date, subject, sent, failed, status FROM job_history ORDER BY id DESC')
            return [{"date": r[0], "subject": r[1], "sent": r[2], "failed": r[3], "status": r[4]} for r in cursor.fetchall()]