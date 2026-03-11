from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_event_confirmation(registration):
    context = {
        'user_name': registration.full_name,
        'event_title': registration.event.title,
        'date': registration.event.date.strftime('%B %d, %Y'),
        'location': registration.event.location,
        'mode': registration.attendance_mode
    }
    
    html_content = render_to_string('emails/event_confirmation.html', context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject=f"Registration Confirmed: {registration.event.title}",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[registration.email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()