import json
from channels.generic.websocket import AsyncWebsocketConsumer

class EventsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Put all clients in a group called "events"
        await self.channel_layer.group_add("events", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Remove from group when disconnected
        await self.channel_layer.group_discard("events", self.channel_name)

    async def receive(self, text_data):
        """
        Handle messages received from client (if we want to support it).
        For now, we’ll ignore since only server sends updates.
        """
        pass

    async def send_event(self, event):
        """
        Called when a new event is broadcast to the group.
        """
        await self.send(text_data=json.dumps({
            "type": event["type"],
            "repo": event["repo"],
            "received_at": event["received_at"],
        }))
