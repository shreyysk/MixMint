import requests
from django.conf import settings

def send_email(to_email, subject, html_content):
    """
    Sends an email using the Resend API.
    """
    if not settings.RESEND_API_KEY:
        print("RESEND_API_KEY not configured. Printing email to console:")
        print(f"To: {to_email}\nSubject: {subject}\nContent: {html_content[:100]}...")
        return None

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
