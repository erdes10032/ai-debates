from django.urls import path

from debates.consumers import (
    DebateConsumer,
)


websocket_urlpatterns = [
    path(
        'ws/debates/<int:debate_id>/',
        DebateConsumer.as_asgi(),
    ),
]