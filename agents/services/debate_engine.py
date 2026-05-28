import logging
import time
from typing import Protocol

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction

from agents.services.openrouter import OpenRouterClient
from agents.services.prompts import DebatePromptBuilder
from agents.services.response_cleaner import DebateResponseCleaner
from debates.concession import (
    CONCESSION_MIN_ROUND,
    active_participants,
    detect_concession,
    should_end_debate_early,
)
from debates.models import (
    Debate,
    DebateMessage,
    DebateParticipant,
    DebateRound,
)


logger = logging.getLogger(__name__)


class LLMClient(Protocol):

    def generate_response(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict],
    ) -> str:
        ...


class DebateEngine:

    MAX_CONTEXT_MESSAGES = 20

    def __init__(
        self,
        *,
        client: LLMClient | None = None,
        prompt_builder: DebatePromptBuilder | None = None,
        response_cleaner: type[DebateResponseCleaner] = DebateResponseCleaner,
        round_delay_seconds: float | None = None,
    ):

        self.client = client or OpenRouterClient()
        self.prompt_builder = prompt_builder or DebatePromptBuilder()
        self.response_cleaner = response_cleaner
        self.round_delay_seconds = (
            round_delay_seconds
            if round_delay_seconds is not None
            else settings.DEBATE_ROUND_DELAY_SECONDS
        )
        self.channel_layer = get_channel_layer()

    def run_debate(
        self,
        *,
        debate: Debate,
    ) -> None:

        logger.info(
            'Starting debate %s',
            debate.id,
        )

        try:

            debate.status = Debate.Status.IN_PROGRESS

            debate.save(
                update_fields=['status'],
            )

            self.broadcast_status(
                debate=debate,
            )

            participants = list(
                debate.participants.order_by(
                    'order',
                    'id',
                ).select_related(
                    'llm_model',
                    'debate_role',
                ),
            )

            if len(participants) < 2:

                raise ValueError(
                    'At least 2 participants required.',
                )

            logger.info(
                'Debate %s: %s participants, %s rounds, '
                'concessions=%s',
                debate.id,
                len(participants),
                debate.rounds_count,
                debate.allow_concessions,
            )

            positions = self.assign_positions(
                participants=participants,
            )

            for participant in participants:

                participant.position = positions[participant.id]

                participant.save(
                    update_fields=['position'],
                )

            history: list[dict] = []

            ended_early = False

            for round_number in range(
                1,
                debate.rounds_count + 1,
            ):

                active = active_participants(participants)

                if not active:

                    logger.info(
                        'Debate %s: no active participants '
                        'before round %s',
                        debate.id,
                        round_number,
                    )

                    ended_early = True

                    break

                logger.info(
                    'Round %s/%s started (%s active participants)',
                    round_number,
                    debate.rounds_count,
                    len(active),
                )

                debate_round = DebateRound.objects.create(
                    debate=debate,
                    number=round_number,
                )

                round_messages = 0

                for participant in participants:

                    if participant.has_conceded:
                        continue

                    label = participant.speaker_label
                    role_name = participant.debate_role.localized_name

                    logger.info(
                        'Round %s: generating for %s',
                        round_number,
                        label,
                    )

                    position = positions[participant.id]

                    if self._message_exists(
                        debate_round=debate_round,
                        participant=participant,
                    ):
                        logger.info(
                            'Skipping duplicate message for '
                            'participant %s in round %s',
                            participant.id,
                            round_number,
                        )
                        continue

                    response = self.client.generate_response(
                        model=participant.llm_model.model_id,
                        system_prompt=(
                            self.prompt_builder.build_system_prompt(
                                debate=debate,
                                participant=participant,
                                position=position,
                                round_number=round_number,
                                total_rounds=debate.rounds_count,
                            )
                        ),
                        messages=[
                            {
                                'role': 'user',
                                'content': (
                                    self.prompt_builder.build_user_prompt(
                                        debate=debate,
                                        round_number=round_number,
                                        position=position,
                                        context=self.build_context(
                                            history=history,
                                        ),
                                        opponent_arguments=(
                                            self.get_recent_opponent_arguments(
                                                history=history,
                                                current_speaker=label,
                                            )
                                        ),
                                    )
                                ),
                            },
                        ],
                    )

                    cleaned_response = self.response_cleaner.clean(
                        response=response,
                    )

                    conceded_this_turn = False

                    if (
                        debate.allow_concessions
                        and round_number >= CONCESSION_MIN_ROUND
                        and participant.debate_role.allows_concession
                        and detect_concession(cleaned_response)
                    ):
                        conceded_this_turn = (
                            self._apply_concession(
                                participant=participant,
                                round_number=round_number,
                            )
                        )

                    with transaction.atomic():

                        message = DebateMessage.objects.create(
                            debate=debate,
                            round=debate_round,
                            participant=participant,
                            speaker_label=label,
                            role_name=role_name,
                            model_name=participant.llm_model.model_id,
                            content=cleaned_response,
                        )

                    history.append(
                        {
                            'speaker': label,
                            'position': position,
                            'content': cleaned_response,
                        },
                    )

                    self.broadcast_message(
                        debate=debate,
                        message=message,
                        round_number=round_number,
                        conceded=conceded_this_turn,
                    )

                    round_messages += 1

                    if self.round_delay_seconds > 0:
                        time.sleep(self.round_delay_seconds)

                    if (
                        debate.allow_concessions
                        and should_end_debate_early(
                            participants,
                        )
                    ):
                        logger.info(
                            'Debate %s: early stop after '
                            'concession in round %s',
                            debate.id,
                            round_number,
                        )

                        ended_early = True

                        break

                logger.info(
                    'Round %s finished with %s messages',
                    round_number,
                    round_messages,
                )

                if ended_early:
                    break

                if round_messages == 0:
                    raise RuntimeError(
                        f'Round {round_number} produced no messages',
                    )

            self._complete_debate(
                debate=debate,
                participants=participants,
                history=history,
                ended_early=ended_early,
            )

        except Exception as error:

            logger.exception(error)

            debate.status = Debate.Status.FAILED

            debate.save(
                update_fields=['status'],
            )

            self.broadcast_status(
                debate=debate,
            )

            raise

    @staticmethod
    def _message_exists(
        *,
        debate_round: DebateRound,
        participant: DebateParticipant,
    ) -> bool:

        return DebateMessage.objects.filter(
            round=debate_round,
            participant=participant,
        ).exists()

    def _apply_concession(
        self,
        *,
        participant: DebateParticipant,
        round_number: int,
    ) -> bool:

        if participant.has_conceded:
            return False

        participant.has_conceded = True

        participant.conceded_at_round = round_number

        participant.save(
            update_fields=[
                'has_conceded',
                'conceded_at_round',
            ],
        )

        logger.info(
            'Participant %s conceded in round %s',
            participant.id,
            round_number,
        )

        return True

    def _complete_debate(
        self,
        *,
        debate: Debate,
        participants: list[DebateParticipant],
        history: list[dict],
        ended_early: bool,
    ) -> None:

        consensus_model = participants[0].llm_model.model_id

        consensus = self._build_consensus(
            debate=debate,
            history=history,
            model=consensus_model,
            ended_early=ended_early,
        )

        debate.consensus = consensus

        debate.status = Debate.Status.COMPLETED

        debate.save(
            update_fields=[
                'consensus',
                'status',
            ],
        )

        self.broadcast_status(
            debate=debate,
        )

        logger.info(
            'Debate %s completed (early=%s)',
            debate.id,
            ended_early,
        )

    def _build_consensus(
        self,
        *,
        debate: Debate,
        history: list[dict],
        model: str,
        ended_early: bool,
    ) -> str:

        context = self.build_context(
            history=history,
        )

        early_note = ''

        if ended_early and debate.allow_concessions:

            conceded = list(
                debate.participants.filter(
                    has_conceded=True,
                ),
            )

            if conceded:

                lines = [
                    (
                        f'- {participant.speaker_label} '
                        f'(round {participant.conceded_at_round})'
                    )
                    for participant in conceded
                ]

                early_note = (
                    '\nThe debate ended early because one side '
                    'conceded. Conceded participants:\n'
                    + '\n'.join(lines)
                    + '\n'
                )

        prompt = self.prompt_builder.build_consensus_prompt(
            debate=debate,
            context=context,
            early_note=early_note,
        )

        response = self.client.generate_response(
            model=model,
            system_prompt=(
                'You are a neutral debate moderator who writes '
                'final consensus summaries.'
            ),
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ],
        )

        return self.response_cleaner.clean(
            response=response,
        )

    def broadcast_message(
        self,
        *,
        debate: Debate,
        message: DebateMessage,
        round_number: int,
        conceded: bool = False,
    ) -> None:

        self._broadcast(
            debate=debate,
            event={
                'type': 'debate.message',
                'message_id': message.id,
                'speaker': message.speaker_label,
                'role': message.role_name,
                'content': message.content,
                'round': round_number,
                'conceded': conceded,
            },
        )

    def broadcast_status(
        self,
        *,
        debate: Debate,
    ) -> None:

        self._broadcast(
            debate=debate,
            event={
                'type': 'debate.status',
                'status': debate.status,
                'consensus': debate.consensus or '',
            },
        )

    def _broadcast(
        self,
        *,
        debate: Debate,
        event: dict,
    ) -> None:

        if not self.channel_layer:
            return

        try:

            async_to_sync(
                self.channel_layer.group_send,
            )(
                f'debate_{debate.id}',
                event,
            )

        except Exception as error:

            logger.warning(
                'WebSocket broadcast failed for debate %s: %s',
                debate.id,
                error,
            )

    def assign_positions(
        self,
        *,
        participants: list[DebateParticipant],
    ) -> dict[int, str]:

        positions = {}

        available_positions = [
            'support',
            'oppose',
        ]

        for index, participant in enumerate(participants):

            if index == 0:

                positions[participant.id] = 'support'

                continue

            if index == len(participants) - 1:

                existing = set(positions.values())

                if len(existing) == 1:

                    if 'support' in existing:

                        positions[participant.id] = 'oppose'

                    else:

                        positions[participant.id] = 'support'

                    continue

            positions[participant.id] = available_positions[
                index % 2
            ]

        logger.info(
            'Assigned positions: %s',
            positions,
        )

        return positions

    def build_context(
        self,
        *,
        history: list[dict],
    ) -> str:

        if not history:

            return 'This is the beginning of the debate.'

        context_parts = []

        recent_messages = history[-self.MAX_CONTEXT_MESSAGES:]

        for item in recent_messages:

            context_parts.append(
                f'{item["speaker"]} ({item["position"]}):\n'
                f'{item["content"]}',
            )

        return '\n\n'.join(context_parts)

    def get_recent_opponent_arguments(
        self,
        *,
        history: list[dict],
        current_speaker: str,
    ) -> str:

        if not history:

            return 'No opponent arguments yet.'

        recent = []

        for item in reversed(history):

            if item['speaker'] != current_speaker:

                recent.append(
                    f'{item["speaker"]}: {item["content"]}',
                )

            if len(recent) >= 3:
                break

        if not recent:

            return 'No direct opponent arguments found.'

        return '\n\n'.join(recent)
