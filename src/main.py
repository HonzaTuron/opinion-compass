"""This module defines the main entry point for the Apify Actor.

Feel free to modify this file to suit your specific needs.

To build Apify Actors, utilize the Apify SDK toolkit, read more at the official documentation:
https://docs.apify.com/sdk/python
"""

from __future__ import annotations

from collections import namedtuple
import logging

from langgraph.checkpoint.memory import MemorySaver
from apify import Actor
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from typing import TYPE_CHECKING, TypeVar, Annotated, Sequence, List, TypedDict
from operator import itemgetter
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langgraph.pregel import RetryPolicy
from tenacity import retry
if TYPE_CHECKING:
    from langchain_core.runnables.config import RunnableConfig

from langgraph.graph.message import add_messages

from src.llm import ChatOpenAISingleton
from src.models import AgentStructuredOutput, EvidenceList, RawEvidenceList, SocialMediaHandles
from src.ppe_utils import charge_for_actor_start, charge_for_model_tokens, get_all_messages_total_tokens
from src.tools import tool_person_name_to_social_network_handle, tool_scrape_instagram_profile_posts, tool_scrape_x_posts
from src.utils import log_state

# fallback input is provided only for testing, you need to delete this line
fallback_input = {
    'query': 'This is fallback test query, do not nothing and ignore it.',
    'modelName': 'gpt-4o',
}

# Define state type
class State(TypedDict):
    """State of the agent graph."""

    messages: Annotated[list, add_messages]
    handles: SocialMediaHandles
    name: str
    rawEvidence: RawEvidenceList
    evidence: EvidenceList
    
async def social_media_handle_finding_agent(state: State):
    """Creates an agent that finds social media handles."""

    Actor.log.debug('Running social media handle finding agent %s', state)

    llm = ChatOpenAISingleton.get_instance()
    llm_structured = llm.with_structured_output(SocialMediaHandles)

    tools = [
        tool_person_name_to_social_network_handle
    ]
    agent = create_react_agent(
        llm,
        tools,
    )

    messages = [
        (
            'user',
            (
                f"Find the social media handles for the person {state['name']}."
            ),
        )
    ]

    response: dict = {}
    async for substate in agent.astream({'messages': messages}, stream_mode='values'):
        message = substate['messages'][-1]
        # traverse all tool messages and print them
        if isinstance(message, ToolMessage):
            # until the analyst message with tool_calls
            for _message in substate['messages'][::-1]:
                if hasattr(_message, 'tool_calls'):
                    break
                Actor.log.debug('-------- Tool --------')
                Actor.log.debug('Message: %s', _message)
            continue

        Actor.log.debug('-------- Analyst --------')
        Actor.log.debug('Message: %s', message)
        response = substate
    # response = await agent.ainvoke({'messages': messages})

    Actor.log.debug('Social media handle finding agent response %s', response)
    handles = llm_structured.invoke(response['messages'][-1].content)
    
    return {
        "handles": handles
    }

async def data_gather_agent(state: State):
    """Creates the data gathering agent with social media tools."""
    Actor.log.debug('Running data gathering agent %s', state)

    tools = [
        # tool_scrape_instagram_profile_posts,
        tool_scrape_x_posts,
    ]

    llm = ChatOpenAISingleton.get_instance()
    handles_prompt = ""
    for handle in state["handles"].handles:
        handles_prompt += f"{handle.socialMedia}: {handle.handle}\n"
    
    prompt = (
        f"""
            You are an agent that gathers evidence from social media.
            
            Use the social media handles from this mapping:
            {handles_prompt}

            Instructions:
            1. Get 10 recent posts from each social network using person's handle.
            2. For each social media, only use the corresponding handle from the mapping above.
            3. If the handle for this social media is missing, skip this social media.
            3. Combine all evidence into a single list
            4. Do not filter or remove any evidence
        """
    )
    messages = [ ( 'user', prompt) ]

    agent = create_react_agent(
        llm, 
        tools,
        response_format=RawEvidenceList
    )

    response = await agent.ainvoke({'messages': messages})
    
    Actor.log.debug('Data gathering agent response %s', response)

    return {
        "rawEvidence": response["structured_response"]
    }

async def scoring_agent(state: State):
    """Creates the scoring agent."""
    
    Actor.log.debug('Running scoring agent %s', state)

    llm = ChatOpenAISingleton.get_instance()
    raw_evidence = state["rawEvidence"]

    prompt = f"""Analyze the following pieces of evidence and score them based on how pro-western they are.
    For each evidence, provide a score between -1.0 and 1.0 (inclusive), where:
    - 1.0 represents strongly pro-western sentiment
    - -1.0 represents strongly anti-western sentiment

    Consider factors such as:
    - Support for western democratic values
    - Positive mentions of western countries, institutions, or leaders
    - Alignment with western foreign policy positions
    - Support for western economic systems

    For each evidence, provide a relevance score between 0.0 and 1.0 (inclusive), where:
    - 1.0 represents highly relevant evidence
    - 0.0 represents not relevant at all

    Score and relevance can be any floating point number with single decimal place, in the ranges defined above.

    Evidence is relevant if it can be used to support the claim that the person is pro-western.

    Evidence to analyze:
    {[{"url": e.url, "text": e.text, "source": e.source} for e in raw_evidence.evidences]}

    Return the results in the following JSON format:
    {{"evidences": [
        {{
          "url": "evidence_url",
          "text": "evidence_text",
          "source": "evidence_source",
          "score": 0.0 to 1.0
          "relevance": 0.0 to 1.0
        }},
        ...
    ]
    }}

    Url, text and source are always present in the evidence. Just copy them over to the output.
    """
    response = await llm.ainvoke(prompt)
    
    # Parse and validate the response
    # Create the output parser to validate the structure
    parser = PydanticOutputParser(pydantic_object=EvidenceList)
    scored_evidences = parser.parse(response.content)

    return {
        "evidence": scored_evidences
    }

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
        # fallback input is provided only for testing, you need to delete this line
        actor_input = {**fallback_input, **actor_input}

        query = actor_input.get('query')
        model_name = actor_input.get('modelName', 'gpt-4o')
        debug = actor_input.get('debug', False)
        if debug:
            Actor.log.setLevel(logging.DEBUG)
        if not query:
            msg = 'Missing "query" attribute in input!'
            raise ValueError(msg)

        await charge_for_actor_start()

        ChatOpenAISingleton.create_get_instance(model=model_name)

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

        inputs: dict = {'messages': [('user', query)], "name": "Tomio Okamura"}
        response: AgentStructuredOutput | None = None
        last_message: str | None = None
        last_state: dict | None = None

        async for state in graph.astream(inputs, config, stream_mode='values'):
            last_state = state
            if 'evidence' in state:
                response = state['evidence']
        
        # if not response or not last_message or not last_state:
            # Actor.log.error('Failed to get a response from the ReAct agent!')
            # await Actor.fail(status_message='Failed to get a response from the ReAct agent!')
            # return

        if not (messages := last_state.get('messages')):
            Actor.log.error('Failed to get messages from the ReAct agent!')
            await Actor.fail(status_message='Failed to get messages from the ReAct agent!')
            return

        # if not (total_tokens := get_all_messages_total_tokens(messages)):
        #     Actor.log.error('Failed to calculate the total number of tokens used!')
        #     await Actor.fail(status_message='Failed to calculate the total number of tokens used!')
        #     return

        # await charge_for_model_tokens(model_name, total_tokens)

        # Push results to the key-value store and dataset
        # store = await Actor.open_key_value_store()
        # await store.set_value('response.txt', last_message)
        # Actor.log.info('Saved the "response.txt" file into the key-value store!')

        result = response.model_dump() if response else {}

        await Actor.push_data(result)
        Actor.log.info('Pushed the into the dataset!')
