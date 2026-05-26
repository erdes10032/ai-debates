from debates.forms import (
    iter_participant_cleaned_data,
)
from debates.models import (
    Debate,
    DebateParticipant,
)


def create_debate_participants(
    *,
    debate: Debate,
    participant_formset,
) -> list[DebateParticipant]:

    participants = []

    for order, cleaned_data in enumerate(
        iter_participant_cleaned_data(
            participant_formset,
        ),
    ):

        participants.append(
            DebateParticipant.objects.create(
                debate=debate,
                llm_model=cleaned_data['llm_model'],
                debate_role=cleaned_data['debate_role'],
                order=order,
            ),
        )

    return participants
