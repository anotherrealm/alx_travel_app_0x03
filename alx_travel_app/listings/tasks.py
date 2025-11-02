from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_booking_confirmation_email(customer_email, booking_details):
    subject = "Booking Confirmation - ALX Travel"
    message = f"Hello! \n\nYour booking is confirmed:\n\n{booking_details}\n\nThank you for choosing ALX Travel!"
    from_email = "noreply@alxtravel.com"

    send_mail(subject, message, from_email, [customer_email])
    return f"Confirmation email sent to {customer_email}"
