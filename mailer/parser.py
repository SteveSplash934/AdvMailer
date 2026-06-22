import csv
import io
from email_validator import validate_email, EmailNotValidError

class RecipientParser:
    @staticmethod
    def parse_file(file_content, filename):
        recipients = []
        content = file_content.decode('utf-8')
        
        if filename.endswith('.csv'):
            reader = csv.reader(io.StringIO(content))
            for row in reader:
                for item in row:
                    email = item.strip()
                    if RecipientParser.is_valid(email):
                        recipients.append(email)
        else: # Treats as .txt
            lines = content.splitlines()
            for line in lines:
                email = line.strip()
                if RecipientParser.is_valid(email):
                    recipients.append(email)
        
        return list(set(recipients)) # Deduplicate

    @staticmethod
    def is_valid(email):
        try:
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False