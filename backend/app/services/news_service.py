"""
News fetching + pre-processing for the AI Tech News Engine.

Sources:
  - Hacker News (Firebase API, no key required)
  - RSS feeds (TechCrunch, The Verge, and any custom feed)

This module does the deterministic, non-AI part of the pipeline:
  fetch -> normalize -> filter (relevance/quality) -> dedup -> rank.

The AI layer (groq_service.summarize_news) then turns the ranked list into the
strict Discord output format. Keeping the heavy lifting here means the engine
still produces a clean, deduplicated, ranked list even if no AI key is set.
"""
from __future__ import annotations

import re
import html
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# Default RSS feeds for the multi-source engine.
DEFAULT_RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
}

# Keywords that mark a story as high-impact tech news.
RELEVANT_KEYWORDS = [
    # AI / ML
    "ai", "a.i.", "artificial intelligence", "machine learning", "ml", "llm",
    "gpt", "openai", "anthropic", "claude", "gemini", "llama", "mistral",
    "neural", "model", "chatbot", "agent",
    # programming / dev
    "programming", "developer", "code", "coding", "python", "javascript",
    "typescript", "rust", "golang", "java", "framework", "open source",
    "open-source", "github", "api", "compiler", "database", "kubernetes",
    "docker", "linux", "kernel",
    # startups / business of tech
    "startup", "funding", "raises", "series a", "series b", "valuation",
    "acquisition", "acquires", "ipo", "venture",
    # cybersecurity
    "security", "cyber", "hack", "breach", "vulnerability", "exploit",
    "ransomware", "malware", "phishing", "zero-day", "zero day", "cve",
    # big tech / hardware
    "google", "apple", "microsoft", "amazon", "meta", "nvidia", "intel",
    "amd", "tesla", "spacex", "tsmc", "qualcomm", "chip", "semiconductor",
    "processor", "gpu", "cpu", "quantum", "cloud", "data center", "datacenter",
    "iphone", "android", "windows", "macos", "browser", "robot", "drone",
]

# Topics that should be dropped even if they slip through.
IRRELEVANT_KEYWORDS = [
    "nba", "nfl", "soccer", "football", "basketball", "celebrity", "movie",
    "box office", "recipe", "horoscope", "kardashian", "gossip", "fashion",
    "lottery",
]

# Low-quality / non-news signals (Ask/Show posts, etc.).
LOW_QUALITY_PREFIXES = ("ask hn:", "tell hn:", "poll:")

_WORD_RE = re.compile(r"[a-z0-9]+")

# Common words ignored when comparing titles for near-duplicate detection.
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "with",
    "new", "now", "its", "is", "are", "as", "by", "at", "from", "into",
    "launches", "launch", "unveils", "reveals", "announces", "announced",
    "introduces", "brings", "gets", "adds", "report", "reports", "says",
}


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------
def _fetch_hacker_news(limit: int) -> list[dict]:
    """Fetch top tech stories from Hacker News."""
    try:
        response = requests.get(HN_TOP_STORIES_URL, timeout=10)
        response.raise_for_status()
        story_ids = response.json()[: max(limit * 3, 30)]

        stories: list[dict] = []
        for story_id in story_ids:
            if len(stories) >= limit:
                break
            try:
                item = requests.get(HN_ITEM_URL.format(story_id), timeout=10).json()
            except Exception:
                continue

            if item and item.get("type") == "story" and item.get("url"):
                stories.append(
                    {
                        "title": item.get("title", "Untitled"),
                        "url": item.get("url"),
                        "source": "Hacker News",
                        "score": int(item.get("score", 0)),
                        "by": item.get("by", "unknown"),
                        "hn_link": f"https://news.ycombinator.com/item?id={story_id}",
                    }
                )
        return stories
    except Exception as e:  # pragma: no cover - network errors
        print(f"[news_service] Hacker News error: {e}")
        return []


def _strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def _fetch_rss(source_name: str, feed_url: str, limit: int) -> list[dict]:
    """Fetch and parse a generic RSS / Atom feed (no extra dependency)."""
    try:
        resp = requests.get(
            feed_url,
            timeout=10,
            headers={"User-Agent": "AI-Tech-News-Engine/1.0"},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:  # pragma: no cover - network/parse errors
        print(f"[news_service] RSS error ({source_name}): {e}")
        return []

    items: list[dict] = []

    # RSS 2.0: channel/item ; Atom: feed/entry
    nodes = root.findall(".//item")
    is_atom = False
    if not nodes:
        # Atom namespace handling
        nodes = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        is_atom = True

    for node in nodes[:limit]:
        if is_atom:
            title_el = node.find("{http://www.w3.org/2005/Atom}title")
            link_el = node.find("{http://www.w3.org/2005/Atom}link")
            summ_el = node.find("{http://www.w3.org/2005/Atom}summary")
            link = link_el.get("href") if link_el is not None else None
        else:
            title_el = node.find("title")
            link_el = node.find("link")
            summ_el = node.find("description")
            link = link_el.text if link_el is not None else None

        title = _strip_tags(title_el.text) if title_el is not None else None
        summary = _strip_tags(summ_el.text) if summ_el is not None else ""

        if title and link:
            items.append(
                {
                    "title": title,
                    "url": link.strip(),
                    "source": source_name,
                    "summary": summary[:400],
                    "score": 0,
                }
            )
    return items


# ---------------------------------------------------------------------------
# Pre-processing: filter -> dedup -> rank
# ---------------------------------------------------------------------------
def _is_relevant(item: dict) -> bool:
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()

    if not text.strip():
        return False
    if item.get("title", "").strip().lower().startswith(LOW_QUALITY_PREFIXES):
        return False
    if any(bad in text for bad in IRRELEVANT_KEYWORDS):
        return False

    # Word-boundary match so "ai" doesn't match "rain"/"email".
    words = set(_WORD_RE.findall(text))
    for kw in RELEVANT_KEYWORDS:
        if " " in kw or "." in kw or "-" in kw:
            if kw in text:
                return True
        elif kw in words:
            return True
    return False


def _norm_title(title: str) -> set[str]:
    words = set(_WORD_RE.findall((title or "").lower()))
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def _dedup(items: list[dict]) -> list[dict]:
    """Remove exact and near-duplicate stories (by URL and title similarity)."""
    seen_urls: set[str] = set()
    kept: list[dict] = []

    for item in items:
        url = (item.get("url") or "").strip().lower().rstrip("/")
        # normalize url (drop query/fragment for dedup)
        try:
            parsed = urlparse(url)
            url_key = f"{parsed.netloc}{parsed.path}".rstrip("/")
        except Exception:
            url_key = url

        if url_key and url_key in seen_urls:
            continue

        title_words = _norm_title(item.get("title", ""))
        is_near_dup = False
        for k in kept:
            other = _norm_title(k.get("title", ""))
            if not title_words or not other:
                continue
            overlap = len(title_words & other) / len(title_words | other)
            if overlap >= 0.4:  # Jaccard similarity threshold (after stopword removal)
                is_near_dup = True
                # Note the cross-source coverage for the AI layer.
                if item.get("source") and item["source"] not in k.get("also_seen_in", []):
                    k.setdefault("also_seen_in", []).append(item["source"])
                break

        if is_near_dup:
            continue

        if url_key:
            seen_urls.add(url_key)
        kept.append(item)

    return kept


def _rank(items: list[dict]) -> list[dict]:
    """Rank by relevance signals: HN score, keyword density, cross-source coverage."""
    def relevance_score(item: dict) -> float:
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        words = set(_WORD_RE.findall(text))
        kw_hits = sum(
            1
            for kw in RELEVANT_KEYWORDS
            if (kw in text if (" " in kw or "-" in kw or "." in kw) else kw in words)
        )
        hn_score = min(item.get("score", 0) / 100.0, 5.0)  # cap influence
        cross_source = len(item.get("also_seen_in", [])) * 2.0
        return kw_hits + hn_score + cross_source

    for item in items:
        item["_rank_score"] = round(relevance_score(item), 2)

    return sorted(items, key=lambda x: x["_rank_score"], reverse=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def fetch_tech_news(
    limit: int = 10,
    sources: list[str] | None = None,
    use_rss: bool = True,
) -> list[dict]:
    """
    Fetch, filter, dedup, and rank high-impact tech news from multiple sources.

    Args:
        limit: max number of items to return after ranking.
        sources: optional subset of RSS source names (keys of DEFAULT_RSS_FEEDS).
        use_rss: include RSS feeds in addition to Hacker News.

    Returns:
        Ranked list of normalized news dicts.
    """
    raw: list[dict] = []
    raw.extend(_fetch_hacker_news(limit=limit))

    if use_rss:
        feeds = DEFAULT_RSS_FEEDS
        if sources:
            feeds = {k: v for k, v in DEFAULT_RSS_FEEDS.items() if k in sources}
        for name, url in feeds.items():
            raw.extend(_fetch_rss(name, url, limit=limit))

    return process_news_items(raw, limit=limit)


def process_news_items(items: list[dict], limit: int = 10) -> list[dict]:
    """
    Run the deterministic engine pipeline on an already-collected list of items.

    Accepts loosely-shaped dicts (e.g. raw input from the user) and normalizes
    them. This is the entry point used by the /process endpoint so callers can
    feed their own raw news data.
    """
    normalized: list[dict] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or it.get("headline") or "").strip()
        url = (it.get("url") or it.get("link") or "").strip()
        if not title:
            continue
        normalized.append(
            {
                "title": title,
                "url": url,
                "source": (it.get("source") or "Unknown").strip(),
                "summary": (it.get("summary") or it.get("description") or "").strip(),
                "score": int(it.get("score", 0) or 0),
            }
        )

    relevant = [it for it in normalized if _is_relevant(it)]
    deduped = _dedup(relevant)
    ranked = _rank(deduped)
    return ranked[:limit]
