from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from src.agents import State, data_gather_agent, scoring_agent, social_media_handle_finding_agent
if TYPE_CHECKING:
    from langchain_core.runnables.config import RunnableConfig

from apify import Actor
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from src.llm import ChatOpenAISingleton
from src.models import AgentStructuredOutput, EvidenceList
from src.ppe_utils import charge_for_actor_start, charge_for_ai_analysis, charge_for_evidence, get_all_messages_total_tokens

def analyze_results(evidenceList: EvidenceList) -> float:
    """Analyzes evidence results by calculating weighted sum of scores weighted by relevance.
        
    Returns:
        float: Weighted sum of scores
    """
    if not evidenceList.evidences:
        return 0.0
        
    weighted_sum = sum(evidence.score * evidence.relevance for evidence in evidenceList.evidences)
    total_relevance = sum(evidence.relevance for evidence in evidenceList.evidences)
    
    if total_relevance == 0:
        return 0.0
        
    return weighted_sum / total_relevance

async def main() -> None:
    """Main entry point for the Apify Actor.

    This coroutine is executed using `asyncio.run()`, so it must remain an asynchronous function for proper execution.
    Asynchronous execution is required for communication with Apify platform, and it also enhances performance in
    the field of web scraping significantly.

    Raises:
        ValueError: If the input is missing required attributes.
    """
    async with Actor:
        # Handle input
        actor_input = await Actor.get_input()

        person = actor_input.get('person')
        opinion = actor_input.get('opinion', 'pro-western')

        debug = False
        if debug:
            Actor.log.setLevel(logging.DEBUG)

        query = f"""
            Find out if {person} identifies with following opinions: {opinion}.
            To do this, find his social media handles and scrape his posts from social media.
            Then, score each post based on how {opinion} it is.
        """

        await charge_for_actor_start()

        ChatOpenAISingleton.create_get_instance(model='gpt-4o')

         # Create the graph
        config: RunnableConfig = {'configurable': {'thread_id': '1', 'debug': debug}}

        # Create the graph
        workflow = StateGraph(State)

        # Add nodes
        workflow.add_node(social_media_handle_finding_agent)
        workflow.add_node(data_gather_agent)
        workflow.add_node(scoring_agent)

        # Add edges
        workflow.add_edge("social_media_handle_finding_agent", "data_gather_agent")
        workflow.add_edge("data_gather_agent", "scoring_agent")
        workflow.add_edge("scoring_agent", END)

        # Set the entry point
        workflow.set_entry_point("social_media_handle_finding_agent")

        # Compile the graph
        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)

        inputs: dict = {'messages': [('user', query)], "name": person}
        response: AgentStructuredOutput | None = None
        last_state: dict | None = None

        async for state in graph.astream(inputs, config, stream_mode='values'):
            last_state = state
            if 'evidence' in state:
                response = state['evidence']
        
        if not response or not last_state or 'messages' not in last_state:
            Actor.log.error('Failed to get a response from the ReAct agent!')
            await Actor.fail(status_message='Failed to get a response from the ReAct agent!')
            return
        
        total_tokens = get_all_messages_total_tokens(last_state["messages"])
        Actor.log.debug('Num tokens: %s', total_tokens)

        result = response.model_dump()
        await charge_for_evidence(len(result['evidences']))
        await Actor.push_data(
            sorted(result['evidences'], key=lambda x: x['relevance'], reverse=True)
        )
        Actor.log.info('Pushed evidence into the dataset!')

        await charge_for_ai_analysis()
        score = analyze_results(response)
        await Actor.set_value('ai-analysis', { "score": score })
        Actor.log.info('The final score is %s', score)

