"""
News Collector - One-shot news and trending topics collector

Usage:
    from news_collector import collect_news, collect_rss, search_news

    # Collect trending topics
    news = collect_news(platforms=["weibo", "zhihu"])

    # Collect RSS feeds
    rss = collect_rss(feeds=[{"id": "hn", "name": "HN", "url": "https://hnrss.org/frontpage"}])

    # Search for keywords
    results = search_news("AI 人工智能")
"""

from .news_collector import (
    collect_news,
    collect_rss,
    search_news,
    list_platforms,
    list_keyword_groups,
    collect_by_topic,
    get_keyword_group,
    parse_keyword_config,
    matches_word_groups,
    matches_keywords,
    PLATFORM_NAMES,
    DEFAULT_PLATFORMS,
    KEYWORD_GROUPS,
)

__all__ = [
    "collect_news",
    "collect_rss",
    "search_news",
    "list_platforms",
    "list_keyword_groups",
    "collect_by_topic",
    "get_keyword_group",
    "parse_keyword_config",
    "matches_word_groups",
    "matches_keywords",
    "PLATFORM_NAMES",
    "DEFAULT_PLATFORMS",
    "KEYWORD_GROUPS",
]

__version__ = "1.0.0"
