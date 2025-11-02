# listings/views.py
import os
import requests
import uuid
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Payment
from django.shortcuts import get_object_or_404
from .tasks import send_payment_confirmation_email

CHAPA_BASE = os.getenv("CHAPA_BASE_URL", "https://api.chapa.co/v1")
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")

def _chapa_headers():
    return {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

@csrf_exempt
def initiate_payment(request):
    """
    POST payload expected:
    {
      "booking_id": 1,
      "amount": 5000,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "currency": "ETB"
    }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    data = request.json() if hasattr(request, "json") else None
    if not data:
        # fallback for common setups
        try:
            import json
            data = json.loads(request.body)
        except Exception:
            return HttpResponseBadRequest("Invalid JSON")

    booking_id = data.get("booking_id")
    amount = data.get("amount")
    email = data.get("email")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    currency = data.get("currency", "ETB")

    if not amount or not email:
        return HttpResponseBadRequest("amount and email required")

    # create local Payment record with pending state
    tx_ref = f"bk-{uuid.uuid4().hex[:12]}"
    payment = Payment.objects.create(
        booking_id=booking_id,
        booking_reference=str(booking_id) if booking_id else tx_ref,
        amount=amount,
        currency=currency,
        transaction_id=tx_ref,
        status=Payment.STATUS_PENDING
    )

    # Chapa initialize endpoint — docs show /transaction/initialize or charges endpoint.
    init_url = f"{CHAPA_BASE}/transaction/initialize"
    payload = {
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": currency,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "callback_url": os.getenv("CHAPA_CALLBACK_URL"),  # optional, define in env
        "return_url": os.getenv("CHAPA_CALLBACK_URL"),
    }

    # try initialize
    try:
        r = requests.post(init_url, json=payload, headers=_chapa_headers(), timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        payment.status = Payment.STATUS_FAILED
        payment.chapa_response = {"error": str(e)}
        payment.save()
        return JsonResponse({"error": "failed to init payment", "details": str(e)}, status=500)

    resp = r.json()
    payment.chapa_response = resp
    payment.save()

    # depending on the returned object, find the checkout/authorization URL
    # Chapa's docs often return a 'data' object with a 'checkout_url' or 'authorization_url'
    checkout_url = None
    if isinstance(resp, dict):
        data = resp.get("data", {})
        checkout_url = data.get("checkout_url") or data.get("authorization_url") or data.get("payment_url") or data.get("url")

    return JsonResponse({
        "message": "payment initiated",
        "tx_ref": tx_ref,
        "checkout_url": checkout_url,
        "chapa_response": resp
    }, status=200)

@csrf_exempt
def verify_payment(request, tx_ref):
    """
    GET or POST webhook/callback can call this endpoint (or your callback handler should call verify)
    """
    # call chapa verify endpoint
    verify_url = f"{CHAPA_BASE}/transaction/verify/{tx_ref}"
    try:
        r = requests.get(verify_url, headers=_chapa_headers(), timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        return JsonResponse({"error": "verify failed", "details": str(e)}, status=500)

    resp = r.json()
    # find status in response: docs show 'data' -> 'status' or similar
    data = resp.get("data", {}) if isinstance(resp, dict) else {}
    status = data.get("status") or data.get("payment_status") or data.get("result")

    # find payment record
    try:
        payment = Payment.objects.get(transaction_id=tx_ref)
    except Payment.DoesNotExist:
        return JsonResponse({"error": "payment record not found"}, status=404)

    payment.chapa_response = resp

    # normalize status mapping depending on Chapa response
    if status and status.lower() in ["successful", "completed", "paid"]:
        payment.status = Payment.STATUS_COMPLETED
        payment.save()
        # send confirmation email in background
        if data.get("customer", {}).get("email"):
            email = data.get("customer", {}).get("email")
        else:
            email = request.GET.get("email") or request.POST.get("email")
        if email:
            subject = "Payment Confirmation"
            message = f"Your payment for booking {payment.booking_reference} was successful. Transaction: {tx_ref}"
            send_payment_confirmation_email.delay(email, subject, message)
    else:
        payment.status = Payment.STATUS_FAILED
        payment.save()

    return JsonResponse({"tx_ref": tx_ref, "status": payment.status, "chapa_response": resp})

