from django.urls import path
from . import consumers  # ✅ we’ll create this in Step 3

websocket_urlpatterns = [
    path("ws/events/", consumers.EventsConsumer.as_asgi()),
]
