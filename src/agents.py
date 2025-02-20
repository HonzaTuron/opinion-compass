from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, TypedDict
if TYPE_CHECKING:
    from langchain_core.runnables.config import RunnableConfig

from apify import Actor
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain.output_parsers import PydanticOutputParser
from langgraph.graph.message import add_messages
from src.llm import ChatOpenAISingleton
from src.models import EvidenceList, RawEvidenceList, SocialMediaHandles
from src.tools import tool_person_name_to_social_network_handle, tool_scrape_instagram_profile_posts, tool_scrape_x_posts

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
    Actor.log.info('Looking for correct social media handles 💻')
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

    response = await agent.ainvoke({'messages': messages})

    Actor.log.debug('Social media handle finding agent response %s', response)
    handles = llm_structured.invoke(response['messages'][-1].content)
    
    return {
        "handles": handles,
        "messages": response['messages'],
    }

async def data_gather_agent(state: State):
    """Creates the data gathering agent with social media tools."""
    Actor.log.info('Gathering data 🌾')
    Actor.log.debug('Running data gathering agent %s', state)

    tools = [
        tool_scrape_instagram_profile_posts,
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
            1. Get 10 most recent posts from each social network using person's handle.
            2. For each social media, only use the corresponding handle from the mapping above.
            3. If the handle for this social media is missing, skip this social media.
            3. Combine all evidence into a single list
            4. Do not filter or remove any evidence
            5. convert all non-asci characters to their closest ascii equivalents
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
        "rawEvidence": response["structured_response"],
        "messages": response['messages'],
    }

async def scoring_agent(state: State):
    """Creates the scoring agent."""
    
    Actor.log.info('Crunching data 🍿')
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
    {[{"text": e.text} for e in raw_evidence.evidences]}

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
        "evidence": scored_evidences,
        "messages": [HumanMessage(content=prompt), response.content]
    }