from __future__ import annotations

from debates.concession import CONCESSION_MIN_ROUND
from debates.models import (
    Debate,
    DebateParticipant,
)


class DebatePromptBuilder:

    @staticmethod
    def get_position_instruction(*, position: str) -> str:

        if position == 'support':
            return (
                'You SUPPORT the main idea or proposition in the topic.'
            )

        return (
            'You OPPOSE the main idea or proposition in the topic.'
        )

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

        if (
            debate.allow_concessions
            and participant.debate_role.allows_concession
        ):

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
            f'YOUR ROLE:\n{role.localized_name}\n\n'
            f'ROLE BEHAVIOR:\n{role.behavior}\n\n'
            f'YOUR POSITION:\n{position_instruction}\n\n'
            f'{concession_block}'
            f'CRITICAL RULES:\n'
            + '\n'.join(rules)
            + '\n'
        )

    @staticmethod
    def build_user_prompt(
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

    @staticmethod
    def build_consensus_prompt(
        *,
        debate: Debate,
        context: str,
        early_note: str,
    ) -> str:

        return (
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
