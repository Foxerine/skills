---
name: news-collector
description:
  Fetches CURRENT hot/trending topics from 17+ Chinese platforms (Weibo, Zhihu, Douyin, Bilibili, 36Kr, IT之家, V2EX, 掘金, etc.).
  Best for "What's trending NOW?" questions - provides 400+ items from platform hot lists that WebSearch cannot access.
  IMPORTANT LIMITATION - Hot lists are ephemeral (refresh every few hours). For investigating SPECIFIC topics/events/people (even recent ones), use WebSearch instead as it indexes historical content.
  Use this skill for bulk trending data collection; use WebSearch for targeted topic research.
license: Apache 2.0
---

# News Collector Skill

A one-shot news and trending topics collector based on TrendRadar. This skill provides direct access to **current** hot topics from 17+ Chinese platforms, delivering bulk trending data that web search cannot access.

## ⚠️ Critical: Understanding Data Characteristics

| Aspect | News Collector | WebSearch |
|--------|---------------|-----------|
| **Data Type** | Hot lists (real-time snapshot) | Search index (persistent) |
| **Lifecycle** | Ephemeral (rotates every few hours) | Persistent (long-term storage) |
| **Best For** | "What's trending NOW?" | "What info exists about X?" |

**Example**: A news story about "Manus" from last week will NOT appear in news-collector results (no longer on hot lists), but WILL appear in WebSearch results (indexed historically).

## ⚡ When to Use This Skill

**USE THIS SKILL:**
- ✅ "现在有什么热点新闻？" → Bulk current trending data
- ✅ "大家在讨论什么？" → Real-time social pulse
- ✅ "微博/知乎/V2EX热榜是什么？" → Platform hot list access
- ✅ "今天的科技新闻" → Current tech trending
- ✅ Need structured data with rankings, URLs, sources from multiple platforms

**USE WebSearch Instead:**
- ❌ Investigating specific topics/events/people (e.g., "Manus是什么？")
- ❌ Searching for specific articles or documents
- ❌ Any topic not currently on hot lists (even if recent)
- ❌ Non-Chinese content or international news
- ❌ Deep research requiring historical context

## 🔄 News Collector vs WebSearch (Complementary Tools)

These tools serve **different purposes** and should be used together:

| Scenario | Best Tool | Reason |
|----------|-----------|--------|
| "现在热门话题是什么？" | **News Collector** | Bulk trending data |
| "Manus/某公司/某人 是什么？" | **WebSearch** | Specific topic research |
| "微博热搜有什么？" | **News Collector** | Platform hot list access |
| "关于X的报道" | **WebSearch** | Historical content |
| "今天大家在讨论什么？" | **News Collector** | Real-time social pulse |
| "X事件的来龙去脉" | **WebSearch** | Deep research |

### News Collector Strengths

| Feature | Capability |
|---------|------------|
| **Data Volume** | 400+ items from 17 platforms in one call |
| **Platform Access** | Direct API access to hot lists (V2EX, 掘金, 贴吧 etc.) |
| **Structured Output** | JSON with title, URL, rank, source |
| **Community Content** | Tech forums WebSearch cannot index |

### Data Coverage

```
News Collector (17 platforms, 400+ items):
├── 社交: 微博(30) + 知乎(20) + 抖音(30) + 贴吧(30)
├── 新闻: 今日头条(30) + 百度(30) + 澎湃(20) + 凤凰(12) + 联合早报(30)
├── 财经: 华尔街见闻(10) + 财联社(13)
├── 科技: 36氪(20) + IT之家(30)
├── 社区: V2EX(30) + 掘金(30)
├── 视频: B站热搜(30)
└── 开发: GitHub Trending(6)
```

## Quick Start

**In Worker Environment (Docker):**

```python
import sys
sys.path.append('/mnt/skills/news-collector/scripts')
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

**Important:** The skill path is `/mnt/skills/news-collector/scripts` (lowercase with hyphen, NOT "News Collector").

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

## Predefined Topics

The skill includes predefined keyword groups with regex pattern support for accurate matching:

| Topic | Keywords | Description |
|-------|----------|-------------|
| `AI` | 11 | AI, ChatGPT, OpenAI, DeepSeek, Claude, 大模型, Sora, Copilot, etc. |
| `科技公司` | 14 | 华为, 腾讯, 阿里, 特斯拉, 苹果, 谷歌, 小米, 字节, etc. |
| `芯片半导体` | 10 | 芯片, 半导体, 光刻机, 台积电, 高通, 联发科, etc. |
| `新能源` | 8 | 电动车, 锂电池, 光伏, 储能, 宁德时代, etc. |
| `机器人` | 8 | 机器人, 具身智能, 人形机器人, 宇树, Figure, etc. |
| `航天` | 7 | 航天, 火箭, 卫星, SpaceX, 蓝色起源, etc. |
| `金融` | 7 | 股市, 基金, 黄金, 比特币, 央行, 汇率, etc. |
| `国际` | 9 | 美国, 俄罗斯, 日本, 乌克兰, 制裁, 关税, etc. |

**Tip:** Use `collect_by_topic("AI")` for the best results - it uses TrendRadar's advanced regex matching for higher accuracy than simple keyword filtering.

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

### collect_by_topic()

Collect news by predefined topic (recommended for most use cases).

```python
def collect_by_topic(
    topic: str,
    platforms: List[str] = None,
    max_items: int = 50,
) -> Dict:
    """
    Collect news by predefined topic/keyword group.

    Args:
        topic: Topic name - "AI", "科技公司", "芯片半导体", "新能源",
               "机器人", "航天", "金融", "国际"
        platforms: Optional list of platform IDs (uses all if None).
        max_items: Maximum items per platform (default: 50).

    Returns:
        Same format as collect_news()
    """
```

## Examples

### Example 0: Collect by Topic (Recommended)

```python
import sys
sys.path.append('/mnt/skills/news-collector/scripts')
from news_collector import collect_by_topic, list_keyword_groups

# Show available topics
print(list_keyword_groups())

# Collect AI-related news from all platforms
result = collect_by_topic("AI")
print(f"Found {result['total_count']} AI-related news items")

# Collect tech company news from specific platforms
result = collect_by_topic("科技公司", platforms=["weibo", "36kr", "ithome"])
```

### Example 1: Get All Trending Topics

```python
import sys
sys.path.append('/mnt/skills/news-collector/scripts')
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
import sys
sys.path.append('/mnt/skills/news-collector/scripts')
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
import sys
sys.path.append('/mnt/skills/news-collector/scripts')
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
import sys
sys.path.append('/mnt/skills/news-collector/scripts')
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
import sys
sys.path.append('/mnt/skills/news-collector/scripts')

import json
from news_collector import collect_news

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
import sys
sys.path.append('/mnt/skills/news-collector/scripts')
from news_collector import collect_news

result = collect_news(platforms=["weibo", "invalid_platform"])

if result["failed"]:
    print(f"Failed platforms: {result['failed']}")

# Partial results are still available
if result["platforms"]:
    print(f"Successfully fetched: {list(result['platforms'].keys())}")
```

## Best Practices

### Recommended Usage Patterns

```python
# 1. For general trending news - use all platforms
result = collect_news()  # 400+ items from 17 platforms

# 2. For topic-specific news - use collect_by_topic (RECOMMENDED)
result = collect_by_topic("AI")  # Pre-configured regex matching

# 3. For platform-specific content
result = collect_news(platforms=["v2ex", "juejin"])  # Tech community
result = collect_news(platforms=["weibo", "zhihu"])  # Social trends
result = collect_news(platforms=["wallstreetcn-hot", "cls-hot"])  # Finance

# 4. For custom keyword filtering with regex
result = collect_news(
    platforms=["weibo", "zhihu", "36kr"],
    keywords=["/华为|鸿蒙/", "/小米|雷军/", "苹果"]  # Regex patterns
)
```

### Platform Selection Guide

| Use Case | Recommended Platforms |
|----------|----------------------|
| 社会热点/娱乐 | `weibo`, `douyin`, `bilibili-hot-search` |
| 科技新闻 | `36kr`, `ithome`, `thepaper` |
| 程序员社区 | `v2ex`, `juejin`, `github` |
| 财经资讯 | `wallstreetcn-hot`, `cls-hot`, `36kr` |
| 问答讨论 | `zhihu`, `tieba` |
| 综合新闻 | `toutiao`, `baidu`, `ifeng` |

## Notes

- All timestamps are in China timezone (Asia/Shanghai)
- Platform availability depends on the NewsNow API
- RSS feeds require valid feed URLs
- Network issues will be reported in the `failed` list
- **This skill accesses platform APIs directly, providing data that web search engines cannot index**
- For best results, prefer `collect_by_topic()` over manual keyword filtering
