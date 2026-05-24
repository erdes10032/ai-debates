
import logging
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from agents.services.openrouter import OpenRouterClient
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


class DebateEngine:

    MAX_CONTEXT_MESSAGES = 20

    ROUND_DELAY_SECONDS = 4

    def __init__(self):

        self.client = OpenRouterClient()

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

                    logger.info(
                        'Round %s: generating for %s',
                        round_number,
                        label,
                    )

                    position = positions[participant.id]

                    response = self.client.generate_response(
                        model=participant.llm_model.model_id,
                        system_prompt=self.build_system_prompt(
                            debate=debate,
                            participant=participant,
                            position=position,
                            round_number=round_number,
                            total_rounds=debate.rounds_count,
                        ),
                        messages=[
                            {
                                'role': 'user',
                                'content': self.build_user_prompt(
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
                                ),
                            },
                        ],
                    )

                    cleaned_response = self.clean_response(
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
                            role_name=participant.debate_role.name,
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

                    time.sleep(self.ROUND_DELAY_SECONDS)

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

        consensus = self.build_consensus(
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

    def build_system_prompt(
        self,
        *,
        debate: Debate,
        participant: DebateParticipant,
        position: str,
        round_number: int,
        total_rounds: int,
    ) -> str:

        role = participant.debate_role

        position_instruction = self.get_position_instruction(
            position=position,
        )

        rules = [
            '- Always answer in EXACTLY the same language '
            'as the debate topic',
            '- Never switch language',
            '- Never explain your reasoning process',
            '- Never say "as an AI"',
            '- Never describe what you plan to do',
            '- Speak naturally like a real debater',
            '- Directly respond to arguments from '
            'other participants',
            '- Attack weak arguments logically',
            '- Give concrete examples',
            '- Be persuasive and intelligent',
            '- Avoid repetition',
            '- Do NOT write stage directions',
            '- Do NOT write analysis',
            '- This is a debate, not an essay',
            '- Keep responses under 300 words',
            '- Write the full argument; do not stop mid-sentence',
        ]

        concession_block = ''

        if debate.allow_concessions and participant.debate_role.allows_concession:

            rules.extend(
                [
                    '- Defend your position while it remains defensible',
                    '- If the core of your position has been refuted, '
                    'you MUST concede honestly',
                    '- To concede, state it clearly in one sentence, e.g. '
                    '"I concede" / "I admit defeat" / "Признаю поражение"',
                    '- Do NOT concede casually or after minor points only',
                ],
            )

            if round_number >= CONCESSION_MIN_ROUND:

                concession_block = (
                    '\nHONESTY CHECK:\n'
                    '- Re-evaluate whether your position still holds\n'
                    '- Concede only if your side has genuinely lost\n'
                )

            if round_number == total_rounds:

                concession_block += (
                    '\nFINAL ROUND:\n'
                    '- If your position is broken, concede explicitly\n'
                )

        else:

            rules.extend(
                [
                    '- Defend your position consistently',
                    '- Do NOT suddenly change sides',
                    '- Do NOT concede or surrender',
                ],
            )

        return (
            f'You are participating in a live AI debate.\n\n'
            f'YOUR ROLE:\n{role.name}\n\n'
            f'ROLE BEHAVIOR:\n{role.behavior}\n\n'
            f'YOUR POSITION:\n{position_instruction}\n\n'
            f'{concession_block}'
            f'CRITICAL RULES:\n'
            + '\n'.join(rules)
            + '\n'
        )

    def build_user_prompt(
        self,
        *,
        debate: Debate,
        round_number: int,
        position: str,
        context: str,
        opponent_arguments: str,
    ) -> str:

        return (
            f'DEBATE TOPIC:\n{debate.topic}\n\n'
            f'ROUND NUMBER:\n{round_number}\n\n'
            f'YOUR POSITION:\n{position}\n\n'
            f'PREVIOUS DISCUSSION:\n{context}\n\n'
            f'OPPONENT ARGUMENTS YOU SHOULD ADDRESS:\n'
            f'{opponent_arguments}\n\n'
            f'YOUR TASK:\n'
            f'- Respond directly to opponents\n'
            f'- Continue the debate naturally\n'
            f'- Defend your side while it remains defensible\n'
            f'- Refute weak arguments\n'
            f'- Add new reasoning\n'
            f'- Sound like a real conversation\n'
            f'- Do NOT repeat previous messages\n'
            f'- Do NOT summarize the whole debate\n'
            f'- Focus on discussion and argumentation\n'
        )

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

    @staticmethod
    def clean_response(
        *,
        response: str,
    ) -> str:

        if not response:

            return (
                'I disagree with the previous arguments and want '
                'to continue the discussion.'
            )

        forbidden_starts = (
            'okay',
            'sure',
            'the user',
            'i need to',
            'i should',
            'let me',
            'here is',
            'analysis:',
            'reasoning:',
            'thoughts:',
            'first, let me',
            'as an ai',
        )

        lines = response.splitlines()

        cleaned_lines = []

        for line in lines:

            stripped = line.strip()

            if not stripped:
                continue

            lower = stripped.lower()

            if (
                len(cleaned_lines) < 3
                and any(
                    lower.startswith(phrase)
                    for phrase in forbidden_starts
                )
            ):
                continue

            cleaned_lines.append(stripped)

        cleaned = '\n'.join(cleaned_lines).strip()

        if not cleaned:
            cleaned = response.strip()

        if len(cleaned) < 20:

            return (
                'I disagree with several points from the previous '
                'speaker. The issue is more complicated than they '
                'describe.'
            )

        return cleaned

    def build_consensus(
        self,
        *,
        debate: Debate,
        history: list[dict],
        model: str,
        ended_early: bool = False,
    ) -> str:

        context = self.build_context(
            history=history,
        )

        early_note = ''

        if ended_early and debate.allow_concessions:

            conceded = [
                participant
                for participant in debate.participants.filter(
                    has_conceded=True,
                )
            ]

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

        prompt = (
            f'DEBATE TOPIC:\n{debate.topic}\n\n'
            f'{early_note}'
            f'DEBATE HISTORY:\n{context}\n\n'
            f'TASK:\n'
            f'- Generate the FINAL CONSENSUS\n'
            f'- Summarize strongest arguments from both sides\n'
            f'- Explain what conclusion the participants reached\n'
            f'- If concessions occurred, reflect them in the summary\n'
            f'- If no full agreement exists, explain the compromise\n'
            f'- Respond in the SAME language as the debate topic\n'
            f'- Write naturally and clearly\n'
            f'- You may use Markdown tables where helpful\n'
            f'- Do NOT explain your analysis\n'
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

        return self.clean_response(
            response=response,
        )

    @staticmethod
    def get_position_instruction(
        *,
        position: str,
    ) -> str:

        if position == 'support':

            return (
                'You SUPPORT the main idea or proposition in the topic.'
            )

        return (
            'You OPPOSE the main idea or proposition in the topic.'
        )
