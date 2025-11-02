## Chapa payment integration

Environment variables required:
- CHAPA_SECRET_KEY
- CHAPA_BASE_URL (default: https://api.chapa.co/v1)
- CHAPA_CALLBACK_URL

Endpoints:
- POST /listings/chapa/initiate/  -> body: { booking_id, amount, email, first_name, last_name }
- GET  /listings/chapa/verify/<tx_ref>/

Testing:
- Use Chapa sandbox keys and follow the sample flow: init -> go to checkout_url -> complete sandbox payment -> verify.
- Ensure Celery worker is running to send emails (if enabled):
  celery -A project worker --loglevel=info

