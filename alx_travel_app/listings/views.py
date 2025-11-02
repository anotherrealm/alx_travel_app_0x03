from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Booking
from .serializers import BookingSerializer
from .tasks import send_booking_confirmation_email

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Prepare booking info
        customer_email = serializer.data.get("customer_email", "test@example.com")
        booking_details = f"Booking ID: {booking['id']}, Destination: {booking['destination']}, Date: {booking['date']}"

        # Trigger Celery email task asynchronously
        send_booking_confirmation_email.delay(customer_email, booking_details)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
