import requests

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def fetch_tech_news(limit: int = 10) -> list[dict]:
    """
    Fetch top tech stories from Hacker News.
    Free API — no key required.
    """
    try:
        response = requests.get(HN_TOP_STORIES_URL, timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:limit * 2]  # Fetch extra in case some lack URLs

        stories = []
        for story_id in story_ids:
            if len(stories) >= limit:
                break
            item_resp = requests.get(HN_ITEM_URL.format(story_id), timeout=10)
            item = item_resp.json()

            # Skip items without a URL (e.g. Ask HN posts)
            if item and item.get("type") == "story" and item.get("url"):
                stories.append({
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url"),
                    "score": item.get("score", 0),
                    "by": item.get("by", "unknown"),
                    "hn_link": f"https://news.ycombinator.com/item?id={story_id}",
                })

        return stories

    except Exception as e:
        print(f"[news_service] Error fetching news: {e}")
        return []