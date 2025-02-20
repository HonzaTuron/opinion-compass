from decimal import ROUND_CEILING, Decimal

from apify import Actor
from langchain_core.messages import AIMessage, BaseMessage
from numpy import number


def get_all_messages_total_tokens(messages: list[BaseMessage]) -> int:
    """Calculates the total number of tokens used in a list of messages.

    Args:
        messages (list[BaseMessage]): A list of messages to calculate the total tokens for.

    Returns:
        int: The total number of tokens used in the messages.

    Raises:
        ValueError: If a message is missing the 'token_usage.total_tokens' in its response metadata.
    """
    sum_tokens = 0
    for message in messages:
        # Skip messages that are not AIMessages
        if not isinstance(message, AIMessage):
            continue

        if not (tokens := message.response_metadata.get('token_usage', {}).get('total_tokens')):
            raise ValueError(f'Missing "token_usage.total_tokens" in response metadata: {message.response_metadata}')
        sum_tokens += tokens

    return sum_tokens

async def charge_for_actor_start() -> None:
    """Charges for the Actor start event.

    This function calculates the memory usage in gigabytes and charges for the Actor start event accordingly.
    """
    count = (Actor.get_env()['memory_mbytes'] or 1024 + 1023) // 1024
    await Actor.charge(event_name='actor-start-gb', count=count)

async def charge_for_ai_analysis() -> None:
    """Charges for the AI analysis.

    This function charges for the AI analysis.
    """
    Actor.log.debug('Charging for AI analysis')
    await Actor.charge(event_name='ai-analysis', count=1)


async def charge_for_evidence(count: int) -> None:
    """Charges for the evidence.

    Args:
        count (int): The number of evidence items to charge for.
    """
    Actor.log.debug('Charging for %s evidences', count)
    await Actor.charge(event_name='evidence', count=count)
