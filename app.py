import os
import asyncio
import threading
import hashlib
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import logging
import aiosmtplib

from mailer.config_manager import ConfigManager
from mailer.parser import RecipientParser
from mailer.sender import MailerEngine
from flask import send_from_directory

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'uploads', 'templates')
ATTACHMENT_FOLDER = os.path.join(BASE_DIR, 'uploads', 'attachments')
LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
IGNORED_FILES = {'.gitkeep', '.gitignore', '.DS_Store', 'desktop.ini'}

os.makedirs(TEMPLATE_FOLDER, exist_ok=True)
os.makedirs(ATTACHMENT_FOLDER, exist_ok=True)
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

@app.route('/SendoraLiteLogo.png')
def serve_logo():
    return send_from_directory('static', 'SendoraLiteLogo.png')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'GET':
        return jsonify(config_mgr.get_all())
    config_mgr.update_from_dict(request.json)
    return jsonify({"status": "success"})

@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    try:
        config_mgr.reset_config()
        return jsonify({"status": "success", "message": "Configuration reset to defaults"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/system/clean-slate', methods=['POST'])
def clean_slate():
    global recipients_list, mailer_engine
    try:
        config_mgr.wipe_database()
        recipients_list = []
        mailer_engine = None

        for folder in [TEMPLATE_FOLDER, ATTACHMENT_FOLDER]:
            if os.path.exists(folder):
                for fname in os.listdir(folder):
                    if fname in IGNORED_FILES:
                        continue
                    fpath = os.path.join(folder, fname)
                    if os.path.isfile(fpath):
                        os.remove(fpath)

        if os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.truncate(0)

        return jsonify({"status": "success", "message": "Clean Slate Reset completed successfully"})
    except Exception as e:
        logger.exception("CRITICAL CLEAN SLATE ERROR")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- SMTP TESTER ---
@app.route('/api/test-smtp', methods=['POST'])
def test_smtp():
    data = request.json
    try:
        smtp_data = data.get('SMTP', {})
        host = smtp_data.get('host')
        port = int(smtp_data.get('port', 587))
        user = smtp_data.get('username')
        password = smtp_data.get('password')

        if not host:
            return jsonify({"error": "SMTP Host is missing"}), 400

        async def check_conn():
            smtp = aiosmtplib.SMTP(hostname=host, port=port, use_tls=(port==465), start_tls=(port!=465), timeout=10)
            await smtp.connect()
            await smtp.login(user, password)
            await smtp.quit()

        asyncio.run(check_conn())
        return jsonify({"message": "Connection Successful!"})
    except Exception as e:
        logger.error(f"SMTP Test Failed: {str(e)}")
        return jsonify({"error": str(e)}), 400

# --- ATTACHMENTS API ---
@app.route('/api/attachments', methods=['GET', 'POST'])
def handle_attachments():
    if request.method == 'POST':
        files = request.files.getlist('files')
        selected = config_mgr.get_selected_attachments()
        for f in files:
            fname = secure_filename(f.filename)
            if fname in IGNORED_FILES or not fname:
                continue
            f.save(os.path.join(ATTACHMENT_FOLDER, fname))
            if fname not in selected:
                selected.append(fname)
        config_mgr.save_selected_attachments(selected)
        visible_files = [f for f in os.listdir(ATTACHMENT_FOLDER) if f not in IGNORED_FILES]
        return jsonify({"status": "success", "files": visible_files, "selected": selected})
    else:
        visible_files = [f for f in os.listdir(ATTACHMENT_FOLDER) if f not in IGNORED_FILES]
        selected = [s for s in config_mgr.get_selected_attachments() if s not in IGNORED_FILES]
        return jsonify({"files": visible_files, "selected": selected})

@app.route('/api/attachments/select', methods=['POST'])
def select_attachments():
    data = request.json or {}
    selected = data.get('selected', [])
    config_mgr.save_selected_attachments(selected)
    return jsonify({"status": "success", "selected": selected})

@app.route('/api/attachments/<filename>', methods=['DELETE'])
def delete_attachment(filename):
    sec_filename = secure_filename(filename)
    path = os.path.join(ATTACHMENT_FOLDER, sec_filename)
    if os.path.exists(path):
        os.remove(path)
    selected = config_mgr.get_selected_attachments()
    if sec_filename in selected:
        selected.remove(sec_filename)
        config_mgr.save_selected_attachments(selected)
    return jsonify({"status": "success"})

# --- TEMPLATES API ---
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

@app.route('/api/templates/<filename>', methods=['DELETE'])
def delete_template(filename):
    sec_filename = secure_filename(filename)
    path = os.path.join(TEMPLATE_FOLDER, sec_filename)
    if os.path.exists(path):
        os.remove(path)
    config_mgr.delete_template(sec_filename)
    return jsonify({"status": "success"})

@app.route('/api/template/content', methods=['GET'])
def get_template_content():
    filename = request.args.get('filename')
    path = os.path.join(TEMPLATE_FOLDER, secure_filename(filename))
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify({"content": f.read()})
    return jsonify({"content": ""})

@app.route('/api/templates/update', methods=['POST'])
def update_template():
    data = request.json
    filename = data.get('filename')
    content = data.get('content')
    path = os.path.join(TEMPLATE_FOLDER, secure_filename(filename))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({"status": "success"})

# --- HISTORY & RECIPIENTS ---
@app.route('/api/history', methods=['GET'])
def get_history():
    return jsonify(config_mgr.get_history())

@app.route('/api/recipients', methods=['POST'])
def upload_recipients():
    global recipients_list
    file = request.files['file']
    recipients_list = RecipientParser.parse_file(file.read(), file.filename)
    return jsonify({"count": len(recipients_list), "recipients": recipients_list})

@app.route('/api/recipients/clear', methods=['POST'])
def clear_recipients():
    global recipients_list
    recipients_list = []
    return jsonify({"status": "success"})

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

# --- MAILER ENGINE CONTROLS ---
@app.route('/api/mailer/stop', methods=['POST'])
def stop_mailer():
    global mailer_engine
    if mailer_engine:
        mailer_engine.stop_requested = True
        logger.warning("STOP SIGNAL SENT TO ENGINE.")
    return jsonify({"status": "stopping"})

@app.route('/api/mailer/start', methods=['POST'])
def start_mailer():
    global mailer_engine, recipients_list
    try:
        if not recipients_list: 
            return jsonify({"error": "Please upload a recipient list first"}), 400
        
        current_config = config_mgr.get_all()
        mode = current_config.get('EMAIL_CONTENT', {}).get('mode', 'html')
        path_key = 'html_path' if mode == 'html' else 'plain_path'
        template_path = current_config.get('EMAIL_CONTENT', {}).get(path_key)

        if not template_path or not os.path.exists(template_path):
            return jsonify({"error": f"No {mode.upper()} template selected. Please choose one."}), 400

        subject = current_config.get('EMAIL_CONTENT', {}).get('subject', 'No Subject')
        job_id = config_mgr.add_job(subject)
        
        # Filter attachments based on user selection and ignored files array
        selected_filenames = set(config_mgr.get_selected_attachments())
        attachments = [
            os.path.join(ATTACHMENT_FOLDER, f) 
            for f in os.listdir(ATTACHMENT_FOLDER) 
            if f not in IGNORED_FILES and f in selected_filenames
        ]
        
        mailer_engine = MailerEngine(current_config, logger)
        
        def run_engine():
            asyncio.run(mailer_engine.send_task(recipients_list, attachments))
            status = "Stopped" if mailer_engine.stop_requested else "Completed"
            config_mgr.update_job(job_id, mailer_engine.progress['sent'], mailer_engine.progress['failed'], status)

        thread = threading.Thread(target=run_engine, daemon=True)
        thread.start()
        
        return jsonify({"status": "started"})
        
    except Exception as e:
        logger.exception("CRITICAL ENGINE START ERROR")
        return jsonify({"error": f"Internal Error: {str(e)}"}), 400

@app.route('/api/mailer/retry', methods=['POST'])
def retry_mailer():
    global mailer_engine
    try:
        if not mailer_engine or not mailer_engine.failed_list:
            return jsonify({"error": "No failed emails to retry"}), 400
            
        failed_emails = [f['email'] for f in mailer_engine.failed_list]
        current_config = config_mgr.get_all()
        
        subject = current_config.get('EMAIL_CONTENT', {}).get('subject', 'No Subject')
        job_id = config_mgr.add_job(subject + " (Retry)")
        
        selected_filenames = set(config_mgr.get_selected_attachments())
        attachments = [
            os.path.join(ATTACHMENT_FOLDER, f) 
            for f in os.listdir(ATTACHMENT_FOLDER) 
            if f not in IGNORED_FILES and f in selected_filenames
        ]
        
        mailer_engine = MailerEngine(current_config, logger)
        
        def run_engine():
            asyncio.run(mailer_engine.send_task(failed_emails, attachments))
            status = "Stopped" if mailer_engine.stop_requested else "Completed"
            config_mgr.update_job(job_id, mailer_engine.progress['sent'], mailer_engine.progress['failed'], status)

        thread = threading.Thread(target=run_engine, daemon=True)
        thread.start()
        
        return jsonify({"status": "started"})
    except Exception as e:
        logger.exception("CRITICAL ENGINE RETRY ERROR")
        return jsonify({"error": f"Internal Error: {str(e)}"}), 400

@app.route('/api/mailer/status')
def mailer_status():
    global mailer_engine
    if not mailer_engine: 
        return jsonify({"running": False})
    
    return jsonify({
        "running": mailer_engine.is_running,
        "progress": mailer_engine.progress,
        "failed_list": mailer_engine.failed_list
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)