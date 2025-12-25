import base64
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GmailTool:
    def __init__(self, creds: Credentials):
        self.service = build('gmail', 'v1', credentials=creds)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(HttpError)
    )
    def fetch_unread_emails(self, max_results=5):
        try:
            results = self.service.users().messages().list(
                userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_data = []

            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='metadata'
                ).execute()
                
                headers = msg.get('payload', {}).get('headers', [])
                subject = next((i['value'] for i in headers if i['name'] == 'Subject'), 'No Subject')
                sender = next((i['value'] for i in headers if i['name'] == 'From'), 'Unknown Sender')
                
                email_data.append({'id': message['id'], 'subject': subject, 'sender': sender})
                
            return email_data
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise

    def send_email(self, to: str, subject: str, body: str):
        # Implementation skipped for brevity, but would use email.mime
        pass
