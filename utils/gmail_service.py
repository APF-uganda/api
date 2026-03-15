import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def send_email(to_email, subject, body):

    creds = Credentials.from_authorized_user_file(
        BASE_DIR / "token.json",
        SCOPES
    )

    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": raw_message}
    ).execute()