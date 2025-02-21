from __future__ import annotations
from typing import Annotated
from langgraph.prebuilt import InjectedState, ToolNode

from apify import Actor
from langchain_core.tools import tool
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from src.models import RawEvidence, EvidenceList

MAX_TEXT_LENGTH = 200
NUM_POSTS_TO_SCRAPE = 10

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

    Actor.log.info('Gathering X/Twitter data 💻.')
    Actor.log.debug('Scraping X/Twitter posts for %s', handle)
    

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
                text=text if len(text) < MAX_TEXT_LENGTH else f"{text[:MAX_TEXT_LENGTH]}...",
                source=source,
            )
        )

    Actor.log.debug('Scraped %d X/Twitter posts for %s', len(evidence), handle)
    return evidence


@tool
async def tool_scrape_instagram_profile_posts(handle: str, max_posts: int = 20) -> list[RawEvidence]:
    """Tool to scrape Instagram profile posts.

    Args:
        handle (str): Instagram handle of the profile to scrape (without the '@' symbol).
        max_posts (int, optional): Maximum number of posts to scrape. Defaults to 30.

    Returns:
        list[Evidence]: List of Evidence objects containing the scraped posts.

    Raises:
        RuntimeError: If the Actor fails to start.
    """
    Actor.log.info('Gathering Instagram data 🤳.')
    Actor.log.debug('Scraping Instagram posts for %s', handle)


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
    evidence: list[RawEvidence] = []
    for item in dataset_items:
        url = item.get('url')
        caption = item.get('caption')
        alt = item.get('alt')

        if not url or not caption:
            Actor.log.warning('Skipping post with missing fields: %s', item)
            continue
        text = caption + ' ' + (alt if alt else '')
        text = text if len(text) < MAX_TEXT_LENGTH else f"{text[:MAX_TEXT_LENGTH]}..."
        evidence.append(
            RawEvidence(
                url=url,
                text=text,
                source='Instagram',
            )
        )

    Actor.log.debug('Scraped %d Instagram posts for %s', len(evidence), handle)
    
    return evidence


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
