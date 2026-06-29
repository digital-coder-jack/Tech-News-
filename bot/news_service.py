import requests

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# Only fetch stories related to these tech topics
TECH_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "python", "javascript", "rust", "golang", "programming", "developer",
    "software", "hardware", "chip", "gpu", "cpu", "nvidia", "amd", "intel",
    "security", "hack", "vulnerability", "breach", "cyber",
    "open source", "github", "linux", "android", "ios", "apple", "google",
    "microsoft", "meta", "openai", "anthropic", "llm", "gpt", "claude",
    "startup", "funding", "api", "cloud", "aws", "docker", "kubernetes",
    "web", "database", "framework", "release", "launch", "update", "version",
    "robot", "quantum", "space", "tesla", "model", "network", "data",
    "privacy", "encryption", "blockchain", "tool", "app", "platform"
]

# Minimum score to be considered important news
MIN_SCORE = 100


def is_tech_story(title: str) -> bool:
    """Check if a story title contains tech-related keywords."""
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in TECH_KEYWORDS)


def fetch_tech_news(limit: int = 10) -> list[dict]:
    """
    Fetch top important tech stories from Hacker News.
    Filters by score (100+) and tech keywords.
    """
    try:
        response = requests.get(HN_TOP_STORIES_URL, timeout=10)
        response.raise_for_status()
        # Fetch top 80 stories to have enough to filter from
        story_ids = response.json()[:80]

        stories = []
        for story_id in story_ids:
            if len(stories) >= limit:
                break

            item = requests.get(HN_ITEM_URL.format(story_id), timeout=10).json()

            if not item:
                continue
            if item.get("type") != "story":
                continue
            if not item.get("url"):
                continue

            title = item.get("title", "")
            score = item.get("score", 0)

            # Only include high scoring tech stories
            if score >= MIN_SCORE and is_tech_story(title):
                stories.append({
                    "title": title,
                    "url": item.get("url"),
                    "score": score,
                    "by": item.get("by", "unknown"),
                })

        # Sort by score — most important first
        stories.sort(key=lambda x: x["score"], reverse=True)
        return stories[:limit]

    except Exception as e:
        print(f"[news_service] Error fetching news: {e}")
        return []
