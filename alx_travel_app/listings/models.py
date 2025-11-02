# listings/models.py
from django.db import models
from django.conf import settings

class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    # If you have Booking model: use ForeignKey. Otherwise keep booking_reference only.
    booking = models.ForeignKey(
        "listings.Booking", null=True, blank=True, on_delete=models.SET_NULL
    )
    booking_reference = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="ETB")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)  # chapa tx_ref or id
    chapa_response = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking_reference or self.transaction_id} - {self.status}"
