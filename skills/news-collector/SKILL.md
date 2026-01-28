---
name: news-collector
description: One-shot news and trending topics collector. Fetches hot topics from various platforms (Weibo, Zhihu, Douyin, etc.) and RSS feeds. Use when Claude needs to gather current news, trending topics, or monitor specific RSS sources.
license: Apache 2.0
---

# News Collector Skill

A lightweight, one-shot news and trending topics collector based on TrendRadar. This skill provides a simple interface to fetch current hot topics from various Chinese social platforms and RSS feeds.

## Quick Start

```python
from news_collector import collect_news, collect_rss

# Collect trending topics from platforms
news = collect_news(
    platforms=["weibo", "zhihu", "douyin"],
    keywords=["AI", "科技", "金融"]  # Optional: filter by keywords
)

# Collect RSS feeds
rss = collect_rss(
    feeds=[
        {"id": "hackernews", "name": "Hacker News", "url": "https://hnrss.org/frontpage"},
    ]
)
```

## Available Platforms

The collector supports the following platforms via the NewsNow API:

### Social Platforms
| Platform ID | Name | Description |
|------------|------|-------------|
| `weibo` | 微博热搜 | Weibo trending topics |
| `zhihu` | 知乎热榜 | Zhihu hot questions |
| `douyin` | 抖音热点 | Douyin trending |
| `tieba` | 贴吧 | Baidu Tieba hot topics |

### News Platforms
| Platform ID | Name | Description |
|------------|------|-------------|
| `toutiao` | 今日头条 | Toutiao news |
| `baidu` | 百度热搜 | Baidu search trends |
| `thepaper` | 澎湃新闻 | The Paper news |
| `ifeng` | 凤凰网 | iFeng news |
| `zaobao` | 联合早报 | Zaobao news |

### Finance Platforms
| Platform ID | Name | Description |
|------------|------|-------------|
| `wallstreetcn-hot` | 华尔街见闻 | Wallstreetcn hot news |
| `cls-hot` | 财联社热门 | CLS finance news |

### Video Platforms
| Platform ID | Name | Description |
|------------|------|-------------|
| `bilibili` | B站热门 | Bilibili trending (alias for bilibili-hot-search) |
| `bilibili-hot-search` | B站热搜 | Bilibili hot search |

### Tech Platforms
| Platform ID | Name | Description |
|------------|------|-------------|
| `36kr` | 36氪 | 36Kr tech news |
| `ithome` | IT之家 | IT Home news |
| `v2ex` | V2EX | V2EX hot topics |
| `juejin` | 掘金 | Juejin tech community |
| `github` | GitHub Trending | GitHub trending repos |

## API Reference

### collect_news()

Collect trending topics from specified platforms.

```python
def collect_news(
    platforms: List[str] = None,
    keywords: List[str] = None,
    max_items: int = 50,
    timeout: int = 10,
) -> Dict:
    """
    Collect trending news from platforms.

    Args:
        platforms: List of platform IDs to fetch. If None, uses default platforms.
        keywords: Optional list of keywords to filter results.
        max_items: Maximum items per platform (default: 50).
        timeout: Request timeout in seconds (default: 10).

    Returns:
        {
            "success": True,
            "timestamp": "2024-01-15 14:30:00",
            "platforms": {
                "weibo": {
                    "name": "微博热搜",
                    "items": [
                        {
                            "title": "热搜标题",
                            "url": "https://...",
                            "rank": 1
                        }
                    ],
                    "count": 50
                }
            },
            "total_count": 150,
            "failed": []
        }
    """
```

### collect_rss()

Collect articles from RSS feeds.

```python
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
        {
            "success": True,
            "timestamp": "2024-01-15 14:30:00",
            "feeds": {
                "hackernews": {
                    "name": "Hacker News",
                    "items": [
                        {
                            "title": "Article title",
                            "url": "https://...",
                            "published_at": "2024-01-15 10:00:00",
                            "author": "author_name",
                            "summary": "Article summary..."
                        }
                    ],
                    "count": 20
                }
            },
            "total_count": 40,
            "failed": []
        }
    """
```

### search_news()

Search for specific topics across all sources.

```python
def search_news(
    query: str,
    platforms: List[str] = None,
    feeds: List[Dict] = None,
) -> Dict:
    """
    Search for news matching a query.

    Args:
        query: Search query (supports multiple keywords separated by space).
        platforms: Optional list of platform IDs.
        feeds: Optional list of RSS feed configs.

    Returns:
        {
            "success": True,
            "query": "AI 人工智能",
            "results": [
                {
                    "title": "...",
                    "url": "...",
                    "source": "weibo",
                    "source_name": "微博热搜",
                    "rank": 5,
                    "match_score": 2  # Number of keywords matched
                }
            ],
            "total_count": 25
        }
    """
```

## Examples

### Example 1: Get All Trending Topics

```python
from news_collector import collect_news

# Fetch from all default platforms
result = collect_news()

if result["success"]:
    for platform_id, platform_data in result["platforms"].items():
        print(f"\n{platform_data['name']}:")
        for item in platform_data["items"][:5]:
            print(f"  {item['rank']}. {item['title']}")
```

### Example 2: Filter by Keywords

```python
from news_collector import collect_news

# Only get AI-related news
result = collect_news(
    platforms=["weibo", "zhihu", "36kr"],
    keywords=["AI", "人工智能", "ChatGPT", "大模型"]
)

for platform_id, platform_data in result["platforms"].items():
    matched = [item for item in platform_data["items"]]
    print(f"{platform_data['name']}: {len(matched)} 条相关新闻")
```

### Example 3: Combine Platforms and RSS

```python
from news_collector import collect_news, collect_rss

# Get platform news
news = collect_news(platforms=["36kr", "ithome"])

# Get RSS feeds
rss = collect_rss(feeds=[
    {"id": "hn", "name": "Hacker News", "url": "https://hnrss.org/frontpage"},
    {"id": "techcrunch", "name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
])

# Combine results
all_items = []
for p_data in news["platforms"].values():
    all_items.extend(p_data["items"])
for f_data in rss["feeds"].values():
    all_items.extend(f_data["items"])

print(f"Total: {len(all_items)} items collected")
```

### Example 4: Quick Search

```python
from news_collector import search_news

# Search across all sources
result = search_news(
    query="OpenAI GPT",
    platforms=["weibo", "zhihu", "36kr"]
)

for item in result["results"]:
    print(f"[{item['source_name']}] {item['title']}")
    print(f"  URL: {item['url']}")
```

## Output Format

The collector returns JSON-serializable dictionaries that can be easily processed or saved:

```python
import json

result = collect_news(platforms=["weibo"])

# Save to file
with open("news.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# Convert to DataFrame
import pandas as pd
items = []
for p_data in result["platforms"].values():
    for item in p_data["items"]:
        item["source"] = p_data["name"]
        items.append(item)
df = pd.DataFrame(items)
```

## Error Handling

The collector gracefully handles errors and reports failed sources:

```python
result = collect_news(platforms=["weibo", "invalid_platform"])

if result["failed"]:
    print(f"Failed platforms: {result['failed']}")

# Partial results are still available
if result["platforms"]:
    print(f"Successfully fetched: {list(result['platforms'].keys())}")
```

## Notes

- All timestamps are in China timezone (Asia/Shanghai)
- Platform availability depends on the NewsNow API
- RSS feeds require valid feed URLs
- Network issues will be reported in the `failed` list
