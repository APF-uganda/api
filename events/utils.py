from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_event_email(user_email, user_name, event_title, event_date, location, status_type):
    """
    status_type: 'RECEIVED' (for initial registration) or 'VERIFIED' (for admin approval)
    """
    # 1. Logic for dynamic content
    if status_type == 'RECEIVED':
        subject = f"Registration Received: {event_title}"
        status_text = "Pending Verification"
        message_body = f"We've received your registration for {event_title}. Our team is reviewing your payment proof."
    else:
        subject = f"Registration Confirmed: {event_title}"
        status_text = "Confirmed & Verified"
        message_body = f"Great news, {user_name}! Your payment for {event_title} has been verified. Your spot is secured."

    # 2. Map variables to the HTML Template
    context = {
        'user_name': user_name,
        'message_body': message_body,
        'status_text': status_text,
        'event_title': event_title,
        'event_date': event_date,
        'location': location,
    }

    # 3. Render HTML and Text fallback
    html_content = render_to_string('emails/event_confirmation.html', context)
    text_content = strip_tags(html_content)

    # 4. Send
    msg = EmailMultiAlternatives(subject, text_content, 'APF Uganda <events@apfuganda.org>', [user_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()