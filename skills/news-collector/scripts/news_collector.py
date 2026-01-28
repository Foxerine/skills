#!/usr/bin/env python
# coding=utf-8
"""
News Collector - One-shot news and trending topics collector

A simplified version of TrendRadar for one-time news collection.
Supports fetching from various Chinese social platforms and RSS feeds.
"""

import json
import random
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict

import requests

# Try to import feedparser for RSS support
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False


# ============================================================================
# Constants
# ============================================================================

DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"
DEFAULT_TIMEZONE = "Asia/Shanghai"

# Default platforms to fetch
DEFAULT_PLATFORMS = [
    ("weibo", "微博热搜"),
    ("zhihu", "知乎热榜"),
    ("douyin", "抖音热点"),
    ("toutiao", "今日头条"),
    ("baidu", "百度热搜"),
]

# Platform name mapping (verified working with NewsNow API)
# Note: Some platforms use specific suffixes like "-hot", "-hot-search"
PLATFORM_NAMES = {
    # Social platforms
    "weibo": "微博热搜",
    "zhihu": "知乎热榜",
    "douyin": "抖音热点",
    "tieba": "贴吧",

    # News platforms
    "toutiao": "今日头条",
    "baidu": "百度热搜",
    "thepaper": "澎湃新闻",
    "ifeng": "凤凰网",
    "zaobao": "联合早报",

    # Finance
    "wallstreetcn-hot": "华尔街见闻",
    "cls-hot": "财联社热门",

    # Video platforms (note: use correct suffix)
    "bilibili": "B站热门",
    "bilibili-hot-search": "B站热搜",

    # Tech platforms
    "36kr": "36氪",
    "ithome": "IT之家",
    "v2ex": "V2EX",
    "juejin": "掘金",
    "github": "GitHub Trending",
}

# Alternative platform IDs (aliases)
PLATFORM_ALIASES = {
    "bilibili": "bilibili-hot-search",  # 推荐使用 bilibili-hot-search
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class NewsItem:
    """Single news item"""
    title: str
    url: str = ""
    mobile_url: str = ""
    rank: int = 0
    source: str = ""
    source_name: str = ""


@dataclass
class RSSItem:
    """Single RSS item"""
    title: str
    url: str = ""
    published_at: str = ""
    author: str = ""
    summary: str = ""
    feed_id: str = ""
    feed_name: str = ""


@dataclass
class CollectionResult:
    """Collection result"""
    success: bool = True
    timestamp: str = ""
    platforms: Dict = field(default_factory=dict)
    feeds: Dict = field(default_factory=dict)
    total_count: int = 0
    failed: List[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# Utility Functions
# ============================================================================

def get_current_time() -> datetime:
    """Get current time in China timezone"""
    try:
        import pytz
        tz = pytz.timezone(DEFAULT_TIMEZONE)
        return datetime.now(tz)
    except ImportError:
        # Fallback: use local time + 8 hours offset for China
        return datetime.now() + timedelta(hours=8)


def format_timestamp(dt: datetime = None) -> str:
    """Format datetime to string"""
    if dt is None:
        dt = get_current_time()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def matches_keywords(text: str, keywords: List[str]) -> bool:
    """Check if text matches any keyword"""
    if not keywords:
        return True
    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    return False


def count_keyword_matches(text: str, keywords: List[str]) -> int:
    """Count how many keywords match the text"""
    if not keywords:
        return 0
    text_lower = text.lower()
    count = 0
    for keyword in keywords:
        if keyword.lower() in text_lower:
            count += 1
    return count


# ============================================================================
# Platform News Collector
# ============================================================================

class PlatformCollector:
    """Collect trending topics from platforms"""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        timeout: int = 10,
        request_interval: int = 100,
    ):
        self.api_url = api_url
        self.timeout = timeout
        self.request_interval = request_interval
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    def fetch_platform(
        self,
        platform_id: str,
        platform_name: str = None,
        max_retries: int = 2,
    ) -> Tuple[List[NewsItem], Optional[str]]:
        """
        Fetch trending topics from a single platform.

        Args:
            platform_id: Platform identifier
            platform_name: Display name (optional)
            max_retries: Maximum retry attempts

        Returns:
            (items, error) tuple
        """
        # Handle platform aliases
        actual_id = PLATFORM_ALIASES.get(platform_id, platform_id)
        if platform_name is None:
            platform_name = PLATFORM_NAMES.get(platform_id, PLATFORM_NAMES.get(actual_id, platform_id))
        platform_id = actual_id

        url = f"{self.api_url}?id={platform_id}&latest"
        items = []
        error = None

        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()
                status = data.get("status", "")

                if status not in ["success", "cache"]:
                    raise ValueError(f"API returned status: {status}")

                for idx, item in enumerate(data.get("items", []), 1):
                    title = item.get("title")
                    if not title or isinstance(title, float):
                        continue
                    title = str(title).strip()
                    if not title:
                        continue

                    news_item = NewsItem(
                        title=title,
                        url=item.get("url", ""),
                        mobile_url=item.get("mobileUrl", ""),
                        rank=idx,
                        source=platform_id,
                        source_name=platform_name,
                    )
                    items.append(news_item)

                return items, None

            except Exception as e:
                error = str(e)
                if attempt < max_retries:
                    wait_time = random.uniform(1, 3) + attempt
                    time.sleep(wait_time)

        return items, error

    def fetch_all(
        self,
        platforms: List[Union[str, Tuple[str, str]]] = None,
        keywords: List[str] = None,
        max_items: int = 50,
    ) -> CollectionResult:
        """
        Fetch from multiple platforms.

        Args:
            platforms: List of platform IDs or (id, name) tuples
            keywords: Optional keywords to filter results
            max_items: Maximum items per platform

        Returns:
            CollectionResult object
        """
        if platforms is None:
            platforms = DEFAULT_PLATFORMS

        result = CollectionResult(
            timestamp=format_timestamp(),
            platforms={},
            failed=[],
        )

        for i, platform in enumerate(platforms):
            # Parse platform info
            if isinstance(platform, tuple):
                platform_id, platform_name = platform
            else:
                platform_id = platform
                platform_name = PLATFORM_NAMES.get(platform_id, platform_id)

            # Fetch data
            items, error = self.fetch_platform(platform_id, platform_name)

            if error:
                result.failed.append(platform_id)
                continue

            # Filter by keywords if specified
            if keywords:
                items = [item for item in items if matches_keywords(item.title, keywords)]

            # Limit items
            if max_items > 0:
                items = items[:max_items]

            # Add to result
            result.platforms[platform_id] = {
                "name": platform_name,
                "items": [asdict(item) for item in items],
                "count": len(items),
            }
            result.total_count += len(items)

            # Request interval (except last one)
            if i < len(platforms) - 1:
                interval = (self.request_interval + random.randint(-20, 20)) / 1000
                time.sleep(max(0.05, interval))

        result.success = len(result.failed) < len(platforms)
        return result


# ============================================================================
# RSS Collector
# ============================================================================

class RSSCollector:
    """Collect articles from RSS feeds"""

    DEFAULT_HEADERS = {
        "User-Agent": "NewsCollector/1.0 RSS Reader",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }

    def __init__(
        self,
        timeout: int = 15,
        request_interval: int = 1000,
        max_age_days: int = 3,
    ):
        if not HAS_FEEDPARSER:
            raise ImportError("feedparser is required for RSS collection. Install with: pip install feedparser")

        self.timeout = timeout
        self.request_interval = request_interval
        self.max_age_days = max_age_days
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def is_fresh(self, published_at: str) -> bool:
        """Check if article is within max_age_days"""
        if self.max_age_days <= 0:
            return True

        if not published_at:
            return True  # Keep items without date

        parsed = self.parse_date(published_at)
        if not parsed:
            return True

        # Make comparison timezone-aware or naive based on parsed result
        now = get_current_time()
        try:
            if parsed.tzinfo is None:
                # Make parsed time timezone-aware
                import pytz
                tz = pytz.timezone(DEFAULT_TIMEZONE)
                parsed = tz.localize(parsed)
        except ImportError:
            pass

        # Compare
        try:
            age = now - parsed
            return age.days <= self.max_age_days
        except TypeError:
            # Handle timezone comparison issues
            return True

    def fetch_feed(
        self,
        feed_id: str,
        feed_name: str,
        feed_url: str,
        max_items: int = 20,
    ) -> Tuple[List[RSSItem], Optional[str]]:
        """
        Fetch a single RSS feed.

        Args:
            feed_id: Feed identifier
            feed_name: Display name
            feed_url: RSS feed URL
            max_items: Maximum items to fetch

        Returns:
            (items, error) tuple
        """
        items = []
        error = None

        try:
            response = self.session.get(feed_url, timeout=self.timeout)
            response.raise_for_status()

            feed = feedparser.parse(response.text)

            if feed.bozo and not feed.entries:
                raise ValueError(f"Failed to parse feed: {feed.bozo_exception}")

            for entry in feed.entries[:max_items] if max_items > 0 else feed.entries:
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Get publication date
                published = entry.get("published") or entry.get("updated") or ""

                # Get summary
                summary = ""
                if entry.get("summary"):
                    summary = entry.summary
                    # Remove HTML tags
                    summary = re.sub(r'<[^>]+>', '', summary)
                    summary = summary[:500] if len(summary) > 500 else summary

                item = RSSItem(
                    title=title,
                    url=entry.get("link", ""),
                    published_at=published,
                    author=entry.get("author", ""),
                    summary=summary.strip(),
                    feed_id=feed_id,
                    feed_name=feed_name,
                )

                # Filter by freshness
                if self.is_fresh(published):
                    items.append(item)

            return items, None

        except Exception as e:
            return [], str(e)

    def fetch_all(
        self,
        feeds: List[Dict],
        max_items: int = 20,
    ) -> CollectionResult:
        """
        Fetch from multiple RSS feeds.

        Args:
            feeds: List of feed configs with id, name, url, max_items
            max_items: Default max items per feed

        Returns:
            CollectionResult object
        """
        result = CollectionResult(
            timestamp=format_timestamp(),
            feeds={},
            failed=[],
        )

        for i, feed_config in enumerate(feeds):
            feed_id = feed_config.get("id", "")
            feed_name = feed_config.get("name", feed_id)
            feed_url = feed_config.get("url", "")
            feed_max_items = feed_config.get("max_items", max_items)

            if not feed_id or not feed_url:
                continue

            items, error = self.fetch_feed(
                feed_id=feed_id,
                feed_name=feed_name,
                feed_url=feed_url,
                max_items=feed_max_items,
            )

            if error:
                result.failed.append(feed_id)
                continue

            result.feeds[feed_id] = {
                "name": feed_name,
                "items": [asdict(item) for item in items],
                "count": len(items),
            }
            result.total_count += len(items)

            # Request interval
            if i < len(feeds) - 1:
                interval = (self.request_interval + random.randint(-200, 200)) / 1000
                time.sleep(max(0.5, interval))

        result.success = len(result.failed) < len(feeds)
        return result


# ============================================================================
# Public API
# ============================================================================

def collect_news(
    platforms: List[Union[str, Tuple[str, str]]] = None,
    keywords: List[str] = None,
    max_items: int = 50,
    timeout: int = 10,
    api_url: str = DEFAULT_API_URL,
) -> Dict:
    """
    Collect trending news from platforms.

    Args:
        platforms: List of platform IDs or (id, name) tuples.
                  If None, uses default platforms.
        keywords: Optional list of keywords to filter results.
        max_items: Maximum items per platform (default: 50).
        timeout: Request timeout in seconds (default: 10).
        api_url: API base URL (optional).

    Returns:
        Dictionary with:
        - success: bool
        - timestamp: str
        - platforms: dict of platform data
        - total_count: int
        - failed: list of failed platform IDs
    """
    collector = PlatformCollector(
        api_url=api_url,
        timeout=timeout,
    )

    result = collector.fetch_all(
        platforms=platforms,
        keywords=keywords,
        max_items=max_items,
    )

    return result.to_dict()


def collect_rss(
    feeds: List[Dict],
    max_items: int = 20,
    max_age_days: int = 3,
    timeout: int = 15,
) -> Dict:
    """
    Collect articles from RSS feeds.

    Args:
        feeds: List of feed configs, each with:
            - id: Unique identifier
            - name: Display name
            - url: RSS feed URL
            - max_items: Optional max items for this feed
        max_items: Default max items per feed (default: 20).
        max_age_days: Filter articles older than N days (default: 3, 0=disable).
        timeout: Request timeout in seconds (default: 15).

    Returns:
        Dictionary with:
        - success: bool
        - timestamp: str
        - feeds: dict of feed data
        - total_count: int
        - failed: list of failed feed IDs
    """
    if not HAS_FEEDPARSER:
        return {
            "success": False,
            "error": "feedparser is required. Install with: pip install feedparser",
            "timestamp": format_timestamp(),
            "feeds": {},
            "total_count": 0,
            "failed": [f.get("id", "") for f in feeds],
        }

    collector = RSSCollector(
        timeout=timeout,
        max_age_days=max_age_days,
    )

    result = collector.fetch_all(
        feeds=feeds,
        max_items=max_items,
    )

    return result.to_dict()


def search_news(
    query: str,
    platforms: List[Union[str, Tuple[str, str]]] = None,
    feeds: List[Dict] = None,
    max_items: int = 50,
) -> Dict:
    """
    Search for news matching a query.

    Args:
        query: Search query (supports multiple keywords separated by space).
        platforms: Optional list of platform IDs.
        feeds: Optional list of RSS feed configs.

    Returns:
        Dictionary with:
        - success: bool
        - query: str
        - results: list of matching items
        - total_count: int
    """
    keywords = [k.strip() for k in query.split() if k.strip()]

    results = []
    failed = []

    # Search platforms
    if platforms is not None or feeds is None:
        platform_result = collect_news(
            platforms=platforms,
            max_items=max_items,
        )
        failed.extend(platform_result.get("failed", []))

        for platform_id, platform_data in platform_result.get("platforms", {}).items():
            for item in platform_data.get("items", []):
                match_score = count_keyword_matches(item["title"], keywords)
                if match_score > 0:
                    results.append({
                        "title": item["title"],
                        "url": item["url"],
                        "source": platform_id,
                        "source_name": platform_data["name"],
                        "rank": item.get("rank", 0),
                        "match_score": match_score,
                        "type": "platform",
                    })

    # Search RSS feeds
    if feeds:
        rss_result = collect_rss(feeds=feeds, max_items=max_items)
        failed.extend(rss_result.get("failed", []))

        for feed_id, feed_data in rss_result.get("feeds", {}).items():
            for item in feed_data.get("items", []):
                # Search in title and summary
                text = item["title"] + " " + item.get("summary", "")
                match_score = count_keyword_matches(text, keywords)
                if match_score > 0:
                    results.append({
                        "title": item["title"],
                        "url": item["url"],
                        "source": feed_id,
                        "source_name": feed_data["name"],
                        "published_at": item.get("published_at", ""),
                        "match_score": match_score,
                        "type": "rss",
                    })

    # Sort by match score
    results.sort(key=lambda x: (-x["match_score"], x.get("rank", 999)))

    return {
        "success": True,
        "query": query,
        "keywords": keywords,
        "results": results,
        "total_count": len(results),
        "failed": failed,
        "timestamp": format_timestamp(),
    }


def list_platforms() -> Dict:
    """
    List all available platforms.

    Returns:
        Dictionary with platform IDs and names.
    """
    return {
        "platforms": PLATFORM_NAMES,
        "default": [p[0] for p in DEFAULT_PLATFORMS],
    }


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="News Collector - One-shot news collection tool")
    parser.add_argument("--platforms", nargs="+", help="Platform IDs to fetch")
    parser.add_argument("--keywords", nargs="+", help="Keywords to filter")
    parser.add_argument("--rss", nargs="+", help="RSS feed URLs")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--max-items", type=int, default=20, help="Max items per source")
    parser.add_argument("--output", type=str, help="Output JSON file")
    parser.add_argument("--list-platforms", action="store_true", help="List available platforms")

    args = parser.parse_args()

    if args.list_platforms:
        platforms = list_platforms()
        print("Available platforms:")
        for pid, pname in platforms["platforms"].items():
            default_mark = " (default)" if pid in platforms["default"] else ""
            print(f"  {pid}: {pname}{default_mark}")
        exit(0)

    result = {}

    if args.search:
        # Search mode
        feeds = None
        if args.rss:
            feeds = [{"id": f"rss_{i}", "name": url, "url": url} for i, url in enumerate(args.rss)]
        result = search_news(
            query=args.search,
            platforms=args.platforms,
            feeds=feeds,
            max_items=args.max_items,
        )
    else:
        # Collect mode
        if args.platforms or not args.rss:
            result["platforms"] = collect_news(
                platforms=args.platforms,
                keywords=args.keywords,
                max_items=args.max_items,
            )

        if args.rss:
            feeds = [{"id": f"rss_{i}", "name": url, "url": url} for i, url in enumerate(args.rss)]
            result["rss"] = collect_rss(feeds=feeds, max_items=args.max_items)

    # Output
    output_str = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"Results saved to: {args.output}")
    else:
        print(output_str)
