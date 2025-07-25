from core import TicketConsumer
from django.urls import path

websocket_urlpatterns = [
    path("ws/tickets/", TicketConsumer.as_asgi()),
]
