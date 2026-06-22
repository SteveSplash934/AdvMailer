import asyncio
import os
import logging
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import aiosmtplib

class MailerEngine:
    def __init__(self, config_data, logger):
        self.config = config_data
        self.logger = logger
        self.is_running = False
        self.progress = {
            "total": 0, "sent": 0, "failed": 0, 
            "current_email": "", "recipient_statuses": {}
        }
        self.failed_list = []
        self.stop_requested = False

    async def send_task(self, recipients, attachments):
        self.is_running = True
        self.progress["total"] = len(recipients)
        self.progress["sent"] = 0
        self.progress["failed"] = 0
        self.progress["recipient_statuses"] = {str(email): "Ready" for email in recipients}
        
        semaphore = asyncio.Semaphore(int(self.config['SETTINGS'].get('concurrency_limit', 5)))
        tasks = [self.send_to_recipient(r, attachments, semaphore) for r in recipients]
        await asyncio.gather(*tasks)
        
        self.is_running = False
        self.logger.info("Dispatch finished or stopped.")

    async def send_to_recipient(self, recipient, attachments, semaphore):
        # CHECK STOP FLAG BEFORE ACQUIRING SEMAPHORE
        if self.stop_requested:
            if self.progress["recipient_statuses"][recipient] == "Ready":
                self.progress["recipient_statuses"][recipient] = "Cancelled"
            return

        async with semaphore:
            # CHECK AGAIN IN CASE IT WAS STOPPED WHILE WAITING IN QUEUE
            if self.stop_requested:
                self.progress["recipient_statuses"][recipient] = "Cancelled"
                return

            self.progress['current_email'] = recipient
            self.progress["recipient_statuses"][recipient] = "Sending..."
            
            max_retries = int(self.config['SETTINGS'].get('max_retries', 3))
            
            for attempt in range(max_retries + 1):
                try:
                    msg = self.create_message(recipient, attachments)
                    smtp_params = {
                        "hostname": self.config['SMTP']['host'],
                        "port": int(self.config['SMTP']['port']),
                        "use_tls": self.config['SMTP'].get('use_ssl', 'false').lower() == 'true',
                        "start_tls": self.config['SMTP'].get('use_tls', 'true').lower() == 'true',
                        "timeout": int(self.config['SETTINGS'].get('timeout', 30))
                    }

                    async with aiosmtplib.SMTP(**smtp_params) as smtp:
                        await smtp.login(self.config['SMTP']['username'], self.config['SMTP']['password'])
                        await smtp.send_message(msg)
                    
                    self.progress['sent'] += 1
                    self.progress["recipient_statuses"][recipient] = "Sent"
                    self.logger.info(f"SUCCESS: {recipient}")
                    return
                except Exception as e:
                    if self.stop_requested:
                        self.progress["recipient_statuses"][recipient] = "Cancelled"
                        return
                        
                    if attempt == max_retries:
                        self.progress['failed'] += 1
                        self.progress["recipient_statuses"][recipient] = "Failed"
                        self.failed_list.append({"email": recipient, "error": str(e)})
                        self.logger.error(f"FINAL FAILURE: {recipient} - {str(e)}")
                    else:
                        await asyncio.sleep(2)

    def create_message(self, recipient, attachments):
        msg = MIMEMultipart()
        msg["From"] = f"{self.config['SENDER']['name']} <{self.config['SENDER']['email']}>"
        msg["To"] = recipient
        msg["Subject"] = self.config['EMAIL_CONTENT'].get('subject', 'Update from System')
        
        mode = self.config['EMAIL_CONTENT']['mode']
        path = self.config['EMAIL_CONTENT']['html_path'] if mode == 'html' else self.config['EMAIL_CONTENT']['plain_path']
        
        with open(path, 'r', encoding='utf-8') as f:
            body = f.read()
        msg.attach(MIMEText(body, mode, 'utf-8'))
        
        # --- ATTACHMENT HANDLING ---
        for filepath in attachments:
            if os.path.exists(filepath):
                ctype, encoding = mimetypes.guess_type(filepath)
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                
                with open(filepath, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(filepath))
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(filepath)}"')
                msg.attach(part)
                
        return msg