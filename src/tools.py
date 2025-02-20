"""This module defines the tools used by the agent.

Feel free to modify or add new tools to suit your specific needs.

To learn how to create a new tool, see:
- https://python.langchain.com/docs/concepts/tools/
- https://python.langchain.com/docs/how_to/#tools
"""

from __future__ import annotations

from apify import Actor
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from src.models import Evidence


@tool
def tool_calculator_sum(numbers: list[int]) -> int:
    """Tool to calculate the sum of a list of numbers.

    Args:
        numbers (list[int]): List of numbers to sum.

    Returns:
        int: Sum of the numbers.
    """
    return sum(numbers)

@tool
async def tool_scrape_x_posts(handle: str, max_posts: int = 30) -> list[Evidence]:
    """Tool to scrape X (Twitter) posts.

    Args:
        handle (str): X/Twitter handle of the profile to scrape (without the '@' symbol).
        max_posts (int, optional): Maximum number of posts to scrape. Defaults to 30.

    Returns:
        list[Evidence]: List of evidence objects scraped from the X/Twitter profile.

    Raises:
        RuntimeError: If the Actor fails to start.
    """
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
    evidence: list[Evidence] = []
    for item in dataset_items:
        url: str | None = item.get('url')
        text: str | None = item.get('text')  # Twitter's text content
        source: str | None = 'X/Twitter'

        # only include posts with all required fields
        if not url or not text:
            Actor.log.warning('Skipping post with missing fields: %s', item)
            continue

        evidence.append(
            Evidence(
                url=url,
                text=text,
                source=source,
            )
        )

    return evidence


@tool
async def tool_scrape_instagram_profile_posts(handle: str, max_posts: int = 30) -> list[Evidence]:
    """Tool to scrape Instagram profile posts.

    Args:
        handle (str): Instagram handle of the profile to scrape (without the '@' symbol).
        max_posts (int, optional): Maximum number of posts to scrape. Defaults to 30.

    Returns:
        list[Evidence]: List of Evidence objects containing the scraped posts.

    Raises:
        RuntimeError: If the Actor fails to start.
    """
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
    posts: list[Evidence] = []
    for item in dataset_items:
        url = item.get('url')
        caption = item.get('caption')
        alt = item.get('alt')

        if not url or not caption:
            Actor.log.warning('Skipping post with missing fields: %s', item)
            continue

        posts.append(
            Evidence(
            url=url,
            text=caption + ' ' + (alt if alt else ''),
            source='Instagram',
            )
        )

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
async def tool_person_name_to_social_network_handle(person_name: str, social_networks: list[str]):
    """Tool to scrape social media handles from Google search results.

    Args:
        person_name (str): Name of the person to search for.
        social_networks (list[str]): Social network to search for handles.

    Returns:
        list[str]: List of social media handles found in the search results.
    """
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

    print(organic_results)
    return organic_results

@tool
async def tool_texts_sentiment_analysis(texts: list[str]):
    """Tool to analyze the sentiment of a list of texts.

    Args:
        texts (list[str]): List of texts to analyze.

    Returns:
        list[dict]: List of dictionaries containing the sentiment analysis results for each text.
    """
    llm = ChatOpenAI(model='gpt-4o')

    result = llm.invoke(input=f'Analyze the sentiment of the following texts: {'. '.join(texts)}')
    
    print(result)
    return result
