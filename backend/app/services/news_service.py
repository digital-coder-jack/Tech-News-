import requests

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def fetch_tech_news(limit: int = 10) -> list[dict]:
    """Fetch top tech stories from Hacker News. Free, no API key needed."""
    try:
        response = requests.get(HN_TOP_STORIES_URL, timeout=10)
        response.raise_for_status()
        story_ids = response.json()[: limit * 2]

        stories = []
        for story_id in story_ids:
            if len(stories) >= limit:
                break
            item = requests.get(HN_ITEM_URL.format(story_id), timeout=10).json()
            if item and item.get("type") == "story" and item.get("url"):
                stories.append({
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url"),
                    "score": item.get("score", 0),
                })

        return stories

    except Exception as e:
        print(f"[news_service] Error: {e}")
        return []
