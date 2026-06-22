import asyncio
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib

class MailerEngine:
    def __init__(self, config_data, logger):
        self.config = config_data
        self.logger = logger
        self.is_running = False
        self.progress = {
            "total": 0, 
            "sent": 0, 
            "failed": 0, 
            "current_email": "",
            "recipient_statuses": {}
        }
        self.failed_list = []
        self.stop_requested = False

    async def send_task(self, recipients, attachments):
            self.is_running = True
            self.progress["total"] = len(recipients)
            self.progress["sent"] = 0
            self.progress["failed"] = 0
            
            # Initialize ALL recipients as 'Ready' so the UI sees them immediately
            self.progress["recipient_statuses"] = {str(email): "Ready" for email in recipients}
            
            semaphore = asyncio.Semaphore(int(self.config['SETTINGS'].get('concurrency_limit', 5)))
            
            # Create tasks for all recipients
            tasks = [self.send_to_recipient(r, attachments, semaphore) for r in recipients]
            await asyncio.gather(*tasks)
            
            self.is_running = False
            self.logger.info("All dispatch tasks finished.")

    def create_message(self, recipient, attachments):
        msg = MIMEMultipart()
        msg["From"] = f"{self.config['SENDER']['name']} <{self.config['SENDER']['email']}>"
        msg["To"] = recipient
        
        # DYNAMIC SUBJECT FROM UI
        msg["Subject"] = self.config['EMAIL_CONTENT'].get('subject', 'Update from System')
        
        mode = self.config['EMAIL_CONTENT']['mode']
        path = self.config['EMAIL_CONTENT']['html_path'] if mode == 'html' else self.config['EMAIL_CONTENT']['plain_path']
        
        with open(path, 'r', encoding='utf-8') as f:
            body = f.read()
        msg.attach(MIMEText(body, mode, 'utf-8'))
        return msg
