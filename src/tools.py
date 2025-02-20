"""This module defines the tools used by the agent.

Feel free to modify or add new tools to suit your specific needs.

To learn how to create a new tool, see:
- https://python.langchain.com/docs/concepts/tools/
- https://python.langchain.com/docs/how_to/#tools
"""

from __future__ import annotations
from typing import Annotated
from langgraph.prebuilt import InjectedState, ToolNode

import json
import os

from apify import Actor
from langchain_core.tools import tool
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from src.models import RawEvidence, RawEvidenceList, Evidence, EvidenceList, SocialMediaHandle

class Cache[T]:
    """A class to handle caching of data to JSON files."""
    
    def __init__(self, cache_name: str):
        self.filename = f"__datacache__/cache_{cache_name}.json"
    
    def read(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                return [T(**item) for item in cached_data]
        return None
    
    def write(self, data: any):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

@tool
async def tool_scrape_x_posts(handle: str, max_posts: int = 30) -> list[RawEvidence]:
    """Tool to scrape X (Twitter) posts.

    Args:
        handle (str): X/Twitter handle of the profile to scrape (without the '@' symbol).
        max_posts (int, optional): Maximum number of posts to scrape. Defaults to 30.

    Returns:
        list[Evidence]: List of evidence objects scraped from the X/Twitter profile.

    Raises:
        RuntimeError: If the Actor fails to start.
    """

    Actor.log.debug('Scraping X/Twitter posts for %s', handle)

    # cache = Cache[RawEvidence]('x.json')
    # data = cache.read()
    # if data:
    #     return data

    run_input = {
        'twitterHandles': [handle],
        'maxItems': max_posts,
        'onlyVerifiedUsers': False,
        'onlyTwitterBlue': False,
        'sort': 'Latest'
    }
    if not (run := await Actor.apify_client.actor('apidojo/tweet-scraper').call(run_input=run_input)):
        msg = 'Failed to start the Actor apidojo/tweet-scraper'
        raise RuntimeError(msg)

    dataset_id = run['defaultDatasetId']
    dataset_items: list[dict] = (await Actor.apify_client.dataset(dataset_id).list_items()).items
    evidence: list[RawEvidence] = []
    for item in dataset_items:
        url: str | None = item.get('url')
        text: str | None = item.get('text')  # Twitter's text content
        source: str | None = 'X/Twitter'

        # only include posts with all required fields
        if not url or not text:
            Actor.log.warning('Skipping post with missing fields: %s', item)
            continue

        evidence.append(
            RawEvidence(
                url=url,
                text=text,
                source=source,
            )
        )

    # cache.write(evidence)
    print('findme', evidence)
    Actor.log.debug('Scraped %d X/Twitter posts for %s', len(evidence), handle)
    return evidence


@tool
async def tool_scrape_instagram_profile_posts(handle: str, max_posts: int = 30) -> list[RawEvidence]:
    """Tool to scrape Instagram profile posts.

    Args:
        handle (str): Instagram handle of the profile to scrape (without the '@' symbol).
        max_posts (int, optional): Maximum number of posts to scrape. Defaults to 30.

    Returns:
        list[Evidence]: List of Evidence objects containing the scraped posts.

    Raises:
        RuntimeError: If the Actor fails to start.
    """
    
    cache = Cache[RawEvidence]('instagram.json')
    data = cache.read()
    if data:
        return data

    run_input = {
        'directUrls': [f'https://www.instagram.com/{handle}/'],
        'resultsLimit': max_posts,
        'resultsType': 'posts',
        'searchLimit': 1,
    }
    if not (run := await Actor.apify_client.actor('apify/instagram-scraper').call(run_input=run_input)):
        msg = 'Failed to start the Actor apify/instagram-scraper'
        raise RuntimeError(msg)

    dataset_id = run['defaultDatasetId']
    dataset_items: list[dict] = (await Actor.apify_client.dataset(dataset_id).list_items()).items
    posts: list[RawEvidence] = []
    for item in dataset_items:
        url = item.get('url')
        caption = item.get('caption')
        alt = item.get('alt')

        if not url or not caption:
            Actor.log.warning('Skipping post with missing fields: %s', item)
            continue

        posts.append(
            RawEvidence(
                url=url,
                text=caption + ' ' + (alt if alt else ''),
                source='Instagram',
            )
        )

    cache.write(posts)
    
    return posts


# @tool
# async def tool_scrape_wikipedia_page(page_title: str) -> Evidence:
#     """Tool to scrape a Wikipedia page.

#     Args:
#         page_title (str): Title of the Wikipedia page to scrape.

#     Returns:
#         Evidence: Evidence object containing the scraped page content.

#     Raises:
#         RuntimeError: If the Actor fails to start.
#     """
#     run_input = {
#         'url': f'https://en.wikipedia.org/wiki/{page_title}',
#     }
#     if not (run := await Actor.apify_client.actor('apify/web-scraper').call(run_input=run_input)):
#         msg = 'Failed to start the Actor apify/web-scraper'
#         raise RuntimeError(msg)

#     dataset_id = run['defaultDatasetId']
#     dataset_items: list[dict] = (await Actor.apify_client.dataset(dataset_id).list_items()).items
#     if not dataset_items:
#         msg = 'Failed to scrape the Wikipedia page'
#         raise RuntimeError(msg)

#     item = dataset_items[0]
#     url = item.get('url')
#     text = item.get('text')

#     if not url or not text:
#         msg = 'Failed to scrape the Wikipedia page'
#         raise RuntimeError(msg)

#     return Evidence(
#         url=url,
#         text=text,
#         source='Wikipedia',
#     )

@tool
async def tool_person_name_to_social_network_handle(person_name: str) -> str:
    """Tool to scrape social media handles from Google search results.

    Args:
        person_name (str): Name of the person to search for.
        social_networks (list[str]): Social network to search for handles.

    Returns:
        list[str]: List of social media handles found in the search results.
    """
    return json.dumps({
        "Twitter/X": "tomio_cz",
        "Instagram": "tomio.cz"
    })

    social_networks = ['Twitter/X', 'Instagram']
    Actor.log.debug('Searching for handles for %s on %s', person_name, social_networks)

    search_query = f'{person_name} {" and ".join(social_networks)}'
    run_input = {
        'queries': search_query,
        'maxPagesPerQuery': 1,
    }
    if not (run := await Actor.apify_client.actor('apify/google-search-scraper').call(run_input=run_input)):
        msg = 'Failed to start the Actor apify/google-search-scraper'
        raise RuntimeError(msg)

    dataset_id = run['defaultDatasetId']
    dataset_items = (await Actor.apify_client.dataset(dataset_id).list_items()).items[0]
    organic_results = dataset_items.get('organicResults')        

    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    
    prompt = f"""Analyze these Google search results and extract social media handles for {person_name}.
    
    Search Results:
    {organic_results}
    
    For each of these social networks: {social_networks}, find the person's handle/username.
    If a handle cannot be found for a network, use an empty string.
    
    Return the results in this JSON format:
    {{
        "network_name": "handle" // without @ symbol
    }}
    
    Only include the requested social networks in the response.
    """

    response = await llm.ainvoke(prompt)
    Actor.log.debug('Handles for %s on %s: %s', person_name, social_networks, response.content)

    return response.content

@tool
async def tool_score_evidences(foo: str, state: Annotated[dict, InjectedState]) -> EvidenceList:
    """Tool to score evidences based on their pro-western sentiment.

    Args:
        evidenceList (EvidenceList): List of evidences to score.

    Returns:
        EvidenceWithScoreList: List of evidences with their corresponding scores.
    """

    print('findme scoring evidences')
    print(state)
    return

    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)

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
    {[{"url": e.url, "text": e.text, "source": e.source} for e in evidenceList.evidences]}

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
    return scored_evidences
