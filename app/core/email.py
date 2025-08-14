import smtplib
from email.mime.text import MIMEText
from app.core.config import settings

def send_email(subject: str, to_email: str, html_body: str):
    if not settings.SMTP_HOST or not settings.EMAILS_FROM:
        # Cho dev: có thể raise hoặc in ra log
        raise RuntimeError("SMTP not configured")

    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.EMAILS_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT or 25) as server:
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAILS_FROM, [to_email], msg.as_string())
