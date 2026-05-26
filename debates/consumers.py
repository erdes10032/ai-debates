import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from debates.models import Debate


logger = logging.getLogger(__name__)


class DebateConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        user = self.scope.get('user')

        if (
            user is None
            or isinstance(user, AnonymousUser)
            or not user.is_authenticated
        ):
            await self.close(code=4401)
            return

        self.debate_id = self.scope['url_route']['kwargs']['debate_id']

        if not await self._user_owns_debate(
            user_id=user.pk,
            debate_id=self.debate_id,
        ):
            await self.close(code=4403)
            return

        self.room_group_name = f'debate_{self.debate_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):

        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def debate_message(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    'type': 'message',
                    'message_id': event['message_id'],
                    'speaker': event['speaker'],
                    'role': event['role'],
                    'content': event['content'],
                    'round': event['round'],
                    'conceded': event.get('conceded', False),
                },
            ),
        )

    async def debate_status(self, event):

        await self.send(
            text_data=json.dumps(
                {
                    'type': 'status',
                    'status': event['status'],
                    'consensus': event.get('consensus', ''),
                },
            ),
        )

    @database_sync_to_async
    def _user_owns_debate(
        self,
        *,
        user_id: int,
        debate_id: int,
    ) -> bool:

        return Debate.objects.filter(
            pk=debate_id,
            user_id=user_id,
        ).exists()
