from celery import shared_task

from agents.services.debate_engine import DebateEngine
from debates.models import Debate


@shared_task
def run_debate_task(
    debate_id: int,
) -> None:

    debate = Debate.objects.get(
        id=debate_id,
    )

    engine = DebateEngine()

    engine.run_debate(
        debate=debate,
    )