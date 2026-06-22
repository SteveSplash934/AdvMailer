import os
import asyncio
import threading
import hashlib
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import logging

from mailer.config_manager import ConfigManager
from mailer.parser import RecipientParser
from mailer.sender import MailerEngine

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'uploads', 'templates')
LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

config_mgr = ConfigManager()
log_file = os.path.join(LOG_FOLDER, "mailer_live.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger("App")

mailer_engine = None
recipients_list = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'GET':
        return jsonify(config_mgr.get_all())
    config_mgr.update_from_dict(request.json)
    return jsonify({"status": "success"})

@app.route('/api/templates/list', methods=['GET'])
def list_templates():
    return jsonify(config_mgr.get_templates())

@app.route('/api/templates/save', methods=['POST'])
def save_template():
    data = request.json
    name = data.get('name')
    content = data.get('content')
    t_type = data.get('type', 'html')
    
    filename = f"{hashlib.md5(name.encode()).hexdigest()}.{t_type}"
    path = os.path.join(TEMPLATE_FOLDER, filename)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    config_mgr.add_template(name, filename, t_type)
    return jsonify({"status": "success", "filename": filename})

@app.route('/api/template/content', methods=['GET'])
def get_template_content():
    filename = request.args.get('filename')
    path = os.path.join(TEMPLATE_FOLDER, secure_filename(filename))
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify({"content": f.read()})
    return jsonify({"content": ""})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            return "".join(f.readlines()[-100:])
    return ""

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    try:
        with open(log_file, 'w') as f:
            f.truncate(0)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/recipients', methods=['POST'])
def upload_recipients():
    global recipients_list
    file = request.files['file']
    recipients_list = RecipientParser.parse_file(file.read(), file.filename)
    return jsonify({"count": len(recipients_list), "recipients": recipients_list})

@app.route('/api/mailer/start', methods=['POST'])
def start_mailer():
    global mailer_engine, recipients_list
    if not recipients_list: 
        return jsonify({"error": "Please upload a recipient list first"}), 400
    
    current_config = config_mgr.get_all()
    
    # Validation: Check if a template is actually selected in the dropdown
    mode = current_config.get('EMAIL_CONTENT', {}).get('mode', 'html')
    # We now check the specific path key based on the mode
    path_key = 'html_path' if mode == 'html' else 'plain_path'
    template_path = current_config.get('EMAIL_CONTENT', {}).get(path_key)

    if not template_path or not os.path.exists(template_path):
        return jsonify({"error": f"No {mode.upper()} template selected. Please go to SMTP Settings and choose one."}), 400

    # Initialize Engine with fresh config
    mailer_engine = MailerEngine(current_config, logger)
    
    # IMPORTANT: Use a wrapper to run the async task in the background thread
    def run_engine():
        asyncio.run(mailer_engine.send_task(recipients_list, []))

    thread = threading.Thread(target=run_engine, daemon=True)
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/mailer/status')
def mailer_status():
    global mailer_engine
    if not mailer_engine: 
        return jsonify({"running": False})
    
    # Return the real-time progress from the active engine
    return jsonify({
        "running": mailer_engine.is_running,
        "progress": mailer_engine.progress,
        "failed_list": mailer_engine.failed_list
    })

@app.route('/api/templates/update', methods=['POST'])
def update_template():
    data = request.json
    filename = data.get('filename')
    content = data.get('content')
    path = os.path.join(TEMPLATE_FOLDER, secure_filename(filename))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)