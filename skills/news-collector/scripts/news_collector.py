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


# ============================================================================
# Keyword Matching System (from TrendRadar upstream)
# ============================================================================

def _parse_word(word: str) -> Dict:
    """
    解析单个词，识别是否为正则表达式，支持显示名称
    (Copied from TrendRadar upstream: trendradar/core/frequency.py)

    Args:
        word: 原始配置行 (e.g. "/京东|刘强东/ => 京东")

    Returns:
        Dict: 包含 word, is_regex, pattern, display_name
    """
    display_name = None

    # 1. 优先处理显示名称 (=>)
    if '=>' in word:
        parts = re.split(r'\s*=>\s*', word, 1)
        word_config = parts[0].strip()
        if len(parts) > 1 and parts[1].strip():
            display_name = parts[1].strip()
    else:
        word_config = word.strip()

    # 2. 解析正则表达式
    regex_match = re.match(r'^/(.+)/[a-z]*$', word_config)

    if regex_match:
        pattern_str = regex_match.group(1)
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            return {
                "word": pattern_str,
                "is_regex": True,
                "pattern": pattern,
                "display_name": display_name,
            }
        except re.error as e:
            print(f"Warning: Invalid regex pattern '/{pattern_str}/': {e}")
            pass

    return {
        "word": word_config,
        "is_regex": False,
        "pattern": None,
        "display_name": display_name
    }


def _word_matches(word_config: Union[str, Dict], title_lower: str) -> bool:
    """
    检查词是否在标题中匹配
    (Copied from TrendRadar upstream)

    Args:
        word_config: 词配置（字符串或字典）
        title_lower: 小写的标题

    Returns:
        是否匹配
    """
    if isinstance(word_config, str):
        return word_config.lower() in title_lower

    if word_config.get("is_regex") and word_config.get("pattern"):
        return bool(word_config["pattern"].search(title_lower))
    else:
        return word_config["word"].lower() in title_lower


def matches_word_groups(
    title: str,
    word_groups: List[Dict],
    filter_words: List = None,
    global_filters: List[str] = None
) -> bool:
    """
    检查标题是否匹配词组规则
    (Copied from TrendRadar upstream: trendradar/core/frequency.py)

    Args:
        title: 标题文本
        word_groups: 词组列表，每个词组包含 required, normal, group_key 等字段
        filter_words: 过滤词列表（可以是字符串列表或字典列表）
        global_filters: 全局过滤词列表

    Returns:
        是否匹配
    """
    # 防御性类型检查
    if not isinstance(title, str):
        title = str(title) if title is not None else ""
    if not title.strip():
        return False

    title_lower = title.lower()

    # 全局过滤检查（优先级最高）
    if global_filters:
        if any(global_word.lower() in title_lower for global_word in global_filters):
            return False

    # 如果没有配置词组，则匹配所有标题
    if not word_groups:
        return True

    # 过滤词检查
    if filter_words:
        for filter_item in filter_words:
            if _word_matches(filter_item, title_lower):
                return False

    # 词组匹配检查
    for group in word_groups:
        required_words = group.get("required", [])
        normal_words = group.get("normal", [])

        # 必须词检查：所有必须词都要匹配
        if required_words:
            all_required_present = all(
                _word_matches(req_item, title_lower) for req_item in required_words
            )
            if not all_required_present:
                continue

        # 普通词检查：任意一个匹配即可
        if normal_words:
            any_normal_present = any(
                _word_matches(normal_item, title_lower) for normal_item in normal_words
            )
            if not any_normal_present:
                continue

        return True

    return False


def parse_keyword_config(config_text: str) -> Tuple[List[Dict], List[Dict], List[str]]:
    """
    解析关键词配置文本（简化版，支持内联配置）

    配置格式说明：
    - 每个词组由空行分隔
    - +词：必须词，所有必须词都要匹配
    - !词：过滤词，匹配则排除
    - 普通词：任意匹配即可
    - /pattern/：正则表达式
    - => 别名：显示名称

    Args:
        config_text: 配置文本

    Returns:
        (词组列表, 过滤词列表, 全局过滤词列表)
    """
    word_groups = [group.strip() for group in config_text.split("\n\n") if group.strip()]

    processed_groups = []
    filter_words = []
    global_filters = []

    current_section = "WORD_GROUPS"

    for group in word_groups:
        lines = [line.strip() for line in group.split("\n")
                 if line.strip() and not line.strip().startswith("#")]

        if not lines:
            continue

        # 检查区域标记
        if lines[0].startswith("[") and lines[0].endswith("]"):
            section_name = lines[0][1:-1].upper()
            if section_name in ("GLOBAL_FILTER", "WORD_GROUPS"):
                current_section = section_name
                lines = lines[1:]

        # 处理全局过滤区域
        if current_section == "GLOBAL_FILTER":
            for line in lines:
                if not line.startswith(("!", "+", "@")):
                    global_filters.append(line)
            continue

        # 处理词组
        words = lines
        group_alias = None

        # 检查组别名
        if words and words[0].startswith("[") and words[0].endswith("]"):
            potential_alias = words[0][1:-1].strip()
            if potential_alias.upper() not in ("GLOBAL_FILTER", "WORD_GROUPS"):
                group_alias = potential_alias
                words = words[1:]

        group_required_words = []
        group_normal_words = []
        group_filter_words = []
        group_max_count = 0

        for word in words:
            if word.startswith("@"):
                try:
                    count = int(word[1:])
                    if count > 0:
                        group_max_count = count
                except (ValueError, IndexError):
                    pass
            elif word.startswith("!"):
                filter_word = word[1:]
                parsed = _parse_word(filter_word)
                filter_words.append(parsed)
                group_filter_words.append(parsed)
            elif word.startswith("+"):
                req_word = word[1:]
                group_required_words.append(_parse_word(req_word))
            else:
                group_normal_words.append(_parse_word(word))

        if group_required_words or group_normal_words:
            if group_normal_words:
                group_key = " ".join(w["word"] for w in group_normal_words)
            else:
                group_key = " ".join(w["word"] for w in group_required_words)

            # 生成显示名称
            if group_alias:
                display_name = group_alias
            else:
                all_words = group_normal_words + group_required_words
                display_parts = [w.get("display_name") or w["word"] for w in all_words]
                display_name = " / ".join(display_parts) if display_parts else None

            processed_groups.append({
                "required": group_required_words,
                "normal": group_normal_words,
                "group_key": group_key,
                "display_name": display_name,
                "max_count": group_max_count,
            })

    return processed_groups, filter_words, global_filters


def matches_keywords(text: str, keywords: List[str], global_filters: List[str] = None) -> bool:
    """
    Check if text matches any keyword (supports regex patterns).

    This is a simplified interface that converts keywords to word groups format
    and uses the full matching system.

    Args:
        text: Text to match against
        keywords: List of keywords (plain text or /regex/)
        global_filters: List of words to exclude (if matched, returns False)

    Returns:
        True if text matches any keyword and doesn't match any filter
    """
    if not text:
        return False

    text_lower = text.lower()

    # Check global filters first (highest priority)
    if global_filters:
        for filter_word in global_filters:
            if filter_word.lower() in text_lower:
                return False

    # If no keywords specified, match all
    if not keywords:
        return True

    # Parse and match keywords
    for keyword in keywords:
        parsed = _parse_word(keyword)
        if _word_matches(parsed, text_lower):
            return True

    return False


def count_keyword_matches(text: str, keywords: List[str]) -> int:
    """Count how many keywords match the text (supports regex patterns)."""
    if not keywords or not text:
        return 0

    text_lower = text.lower()
    count = 0

    for keyword in keywords:
        parsed = _parse_word(keyword)
        if _word_matches(parsed, text_lower):
            count += 1

    return count


def get_matched_keyword(text: str, keywords: List[str]) -> Optional[str]:
    """Get the first matched keyword (with display name if available)."""
    if not keywords or not text:
        return None

    text_lower = text.lower()

    for keyword in keywords:
        parsed = _parse_word(keyword)
        if _word_matches(parsed, text_lower):
            return parsed.get("display_name") or parsed["word"]

    return None


# ============================================================================
# Predefined Keyword Groups (from TrendRadar)
# ============================================================================

KEYWORD_GROUPS = {
    "科技公司": [
        "/华为|任正非|余承东|鸿蒙|海思/",
        "/比亚迪|王传福|方程豹|腾势/",
        "/大疆|汪滔/",
        "/特斯拉|马斯克|Tesla|Elon.?Musk/",
        "/英伟达|黄仁勋|NVIDIA/",
        "/微软|Microsoft|Windows|Azure/",
        "/谷歌|Google|Android|YouTube/",
        "/苹果|iPhone|iPad|MacBook|iOS/",
        "/腾讯|马化腾|微信/",
        "/阿里|马云|淘宝|天猫|支付宝/",
        "/字节|张一鸣|抖音|TikTok/",
        "/京东|刘强东/",
        "/百度|李彦宏/",
        "/小米|雷军/",
    ],
    "AI": [
        # Use word boundary \b for AI matching (works with re.IGNORECASE)
        "/\\bAI\\b/",
        "人工智能",
        "/OpenAI|ChatGPT|GPT-4|GPT-5|GPT4|GPT5/",
        "/Claude|Anthropic/",
        "/深度求索|DeepSeek/",
        "/大模型|LLM/",
        "/机器学习|深度学习/",
        "智能体",
        "/Gemini|Bard/",
        "/Sora|文生视频/",
        "/Copilot|GitHub.?Copilot/",
    ],
    "芯片半导体": [
        "芯片",
        "半导体",
        "光刻机",
        "/台积电|TSMC/",
        "/中芯|SMIC/",
        "/Intel|英特尔/",
        "/AMD|锐龙|Ryzen/",
        "/ASML|阿斯麦/",
        "/高通|Qualcomm/",
        "/联发科|MediaTek/",
    ],
    "新能源": [
        "新能源",
        "/电动车|电动汽车|纯电/",
        "锂电池",
        "/光伏|太阳能/",
        "储能",
        "氢能",
        "充电桩",
        "/宁德时代|CATL/",
    ],
    "机器人": [
        "机器人",
        "/机器狗|四足/",
        "具身智能",
        "/人形机器人|仿人/",
        "/宇树|Unitree/",
        "/智元|AgiBot/",
        "/波士顿动力|Boston.?Dynamics/",
        "/Figure|1X|Agility/",
    ],
    "航天": [
        "/航天|太空/",
        "/火箭|发射/",
        "/卫星|空间站/",
        "/月球|登月/",
        "/火星|深空/",
        "/SpaceX|星舰|Starship/",
        "/蓝色起源|Blue.?Origin/",
    ],
    "金融": [
        "/股市|A股|港股|美股/",
        "/基金|ETF/",
        "黄金",
        "/比特币|加密货币|数字货币|BTC|ETH/",
        "/央行|美联储|降息|加息/",
        "汇率",
        "/人民币|美元/",
    ],
    "国际": [
        "/美国|拜登|特朗普|Trump|Biden/",
        "/俄罗斯|普京|Putin/",
        "/日本|岸田/",
        "/韩国|尹锡悦/",
        "/欧盟|欧洲/",
        "/中东|以色列|巴勒斯坦/",
        "制裁",
        "关税",
        "/乌克兰|俄乌/",
    ],
}

# Pre-parse keyword groups for better performance
_PARSED_KEYWORD_GROUPS: Dict[str, List[Dict]] = {}


def _get_parsed_keyword_group(group_name: str) -> List[Dict]:
    """Get parsed keyword group with caching."""
    if group_name not in _PARSED_KEYWORD_GROUPS:
        keywords = KEYWORD_GROUPS.get(group_name, [])
        _PARSED_KEYWORD_GROUPS[group_name] = [_parse_word(k) for k in keywords]
    return _PARSED_KEYWORD_GROUPS[group_name]


def get_keyword_group(group_name: str) -> List[str]:
    """Get keywords for a predefined group"""
    return KEYWORD_GROUPS.get(group_name, [])


# ============================================================================
# Platform News Collector (based on TrendRadar DataFetcher)
# ============================================================================

class PlatformCollector:
    """
    Collect trending topics from platforms.
    Based on TrendRadar upstream DataFetcher (trendradar/crawler/fetcher.py)
    """

    # Default headers matching upstream
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        proxy_url: Optional[str] = None,
        timeout: int = 10,
        request_interval: int = 100,
    ):
        """
        初始化数据获取器

        Args:
            api_url: API 基础 URL
            proxy_url: 代理服务器 URL（可选）
            timeout: 请求超时时间（秒）
            request_interval: 请求间隔（毫秒）
        """
        self.api_url = api_url
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.request_interval = request_interval
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    def fetch_data(
        self,
        id_info: Union[str, Tuple[str, str]],
        max_retries: int = 2,
        min_retry_wait: int = 3,
        max_retry_wait: int = 5,
    ) -> Tuple[Optional[str], str, str]:
        """
        获取指定ID数据，支持重试
        (From TrendRadar upstream: trendradar/crawler/fetcher.py)

        Args:
            id_info: 平台ID 或 (平台ID, 别名) 元组
            max_retries: 最大重试次数
            min_retry_wait: 最小重试等待时间（秒）
            max_retry_wait: 最大重试等待时间（秒）

        Returns:
            (响应文本, 平台ID, 别名) 元组，失败时响应文本为 None
        """
        if isinstance(id_info, tuple):
            id_value, alias = id_info
        else:
            id_value = id_info
            alias = id_value

        # Handle platform aliases
        actual_id = PLATFORM_ALIASES.get(id_value, id_value)
        id_value = actual_id

        url = f"{self.api_url}?id={id_value}&latest"

        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(
                    url,
                    proxies=proxies,
                    headers=self.DEFAULT_HEADERS,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data_text = response.text
                data_json = json.loads(data_text)

                status = data_json.get("status", "未知")
                if status not in ["success", "cache"]:
                    raise ValueError(f"响应状态异常: {status}")

                return data_text, id_value, alias

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(min_retry_wait, max_retry_wait)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    time.sleep(wait_time)
                else:
                    return None, id_value, alias

        return None, id_value, alias

    def crawl_websites(
        self,
        ids_list: List[Union[str, Tuple[str, str]]],
        request_interval: int = None,
    ) -> Tuple[Dict, Dict, List]:
        """
        爬取多个网站数据
        (From TrendRadar upstream: trendradar/crawler/fetcher.py)

        Args:
            ids_list: 平台ID列表，每个元素可以是字符串或 (平台ID, 别名) 元组
            request_interval: 请求间隔（毫秒）

        Returns:
            (结果字典, ID到名称的映射, 失败ID列表) 元组
        """
        if request_interval is None:
            request_interval = self.request_interval

        results = {}
        id_to_name = {}
        failed_ids = []

        for i, id_info in enumerate(ids_list):
            if isinstance(id_info, tuple):
                id_value, name = id_info
            else:
                id_value = id_info
                name = PLATFORM_NAMES.get(id_value, id_value)

            # Handle aliases
            actual_id = PLATFORM_ALIASES.get(id_value, id_value)

            id_to_name[actual_id] = name
            response, returned_id, _ = self.fetch_data((actual_id, name))

            if response:
                try:
                    data = json.loads(response)
                    results[actual_id] = {}

                    for index, item in enumerate(data.get("items", []), 1):
                        title = item.get("title")
                        # 跳过无效标题（None、float、空字符串）
                        if title is None or isinstance(title, float) or not str(title).strip():
                            continue
                        title = str(title).strip()
                        url = item.get("url", "")
                        mobile_url = item.get("mobileUrl", "")

                        if title in results[actual_id]:
                            results[actual_id][title]["ranks"].append(index)
                        else:
                            results[actual_id][title] = {
                                "ranks": [index],
                                "url": url,
                                "mobileUrl": mobile_url,
                            }
                except json.JSONDecodeError:
                    failed_ids.append(actual_id)
                except Exception as e:
                    failed_ids.append(actual_id)
            else:
                failed_ids.append(actual_id)

            # 请求间隔（除了最后一个）
            if i < len(ids_list) - 1:
                actual_interval = request_interval + random.randint(-10, 20)
                actual_interval = max(50, actual_interval)
                time.sleep(actual_interval / 1000)

        return results, id_to_name, failed_ids

    def fetch_platform(
        self,
        platform_id: str,
        platform_name: str = None,
        max_retries: int = 2,
    ) -> Tuple[List[NewsItem], Optional[str]]:
        """
        Fetch trending topics from a single platform.
        Higher-level interface that returns NewsItem list.

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

        response_text, returned_id, _ = self.fetch_data(
            (actual_id, platform_name),
            max_retries=max_retries
        )

        items = []
        error = None

        if response_text:
            try:
                data = json.loads(response_text)
                for idx, item in enumerate(data.get("items", []), 1):
                    title = item.get("title")
                    if title is None or isinstance(title, float) or not str(title).strip():
                        continue
                    title = str(title).strip()

                    news_item = NewsItem(
                        title=title,
                        url=item.get("url", ""),
                        mobile_url=item.get("mobileUrl", ""),
                        rank=idx,
                        source=returned_id,
                        source_name=platform_name,
                    )
                    items.append(news_item)
            except Exception as e:
                error = str(e)
        else:
            error = f"Failed to fetch {actual_id}"

        return items, error

    def fetch_all(
        self,
        platforms: List[Union[str, Tuple[str, str]]] = None,
        keywords: List[str] = None,
        max_items: int = 50,
        word_groups: List[Dict] = None,
        filter_words: List = None,
        global_filters: List[str] = None,
    ) -> CollectionResult:
        """
        Fetch from multiple platforms.

        Args:
            platforms: List of platform IDs or (id, name) tuples
            keywords: Optional keywords to filter results (simple mode)
            max_items: Maximum items per platform
            word_groups: Word groups for advanced matching (TrendRadar mode)
            filter_words: Filter words to exclude
            global_filters: Global filter words

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

        # Use crawl_websites for batch fetching
        ids_list = []
        for platform in platforms:
            if isinstance(platform, tuple):
                ids_list.append(platform)
            else:
                name = PLATFORM_NAMES.get(platform, platform)
                ids_list.append((platform, name))

        raw_results, id_to_name, failed_ids = self.crawl_websites(ids_list)
        result.failed = failed_ids

        for platform_id, titles_data in raw_results.items():
            platform_name = id_to_name.get(platform_id, platform_id)
            items = []

            for title, data in titles_data.items():
                # Get best rank
                rank = min(data["ranks"]) if data["ranks"] else 0

                # Apply filtering
                should_include = True

                if word_groups is not None:
                    # Advanced TrendRadar matching
                    should_include = matches_word_groups(
                        title, word_groups, filter_words, global_filters
                    )
                elif keywords:
                    # Simple keyword matching
                    should_include = matches_keywords(title, keywords, global_filters)

                if should_include:
                    news_item = NewsItem(
                        title=title,
                        url=data.get("url", ""),
                        mobile_url=data.get("mobileUrl", ""),
                        rank=rank,
                        source=platform_id,
                        source_name=platform_name,
                    )
                    items.append(news_item)

            # Sort by rank
            items.sort(key=lambda x: x.rank)

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
    proxy_url: Optional[str] = None,
    word_groups: List[Dict] = None,
    filter_words: List = None,
    global_filters: List[str] = None,
) -> Dict:
    """
    Collect trending news from platforms.

    Args:
        platforms: List of platform IDs or (id, name) tuples.
                  If None, uses default platforms.
        keywords: Optional list of keywords to filter results (simple mode).
        max_items: Maximum items per platform (default: 50).
        timeout: Request timeout in seconds (default: 10).
        api_url: API base URL (optional).
        proxy_url: Proxy server URL (optional).
        word_groups: Word groups for advanced matching (TrendRadar mode).
        filter_words: Filter words to exclude.
        global_filters: Global filter words.

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
        proxy_url=proxy_url,
        timeout=timeout,
    )

    result = collector.fetch_all(
        platforms=platforms,
        keywords=keywords,
        max_items=max_items,
        word_groups=word_groups,
        filter_words=filter_words,
        global_filters=global_filters,
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


def list_keyword_groups() -> Dict:
    """
    List all predefined keyword groups.

    Returns:
        Dictionary with group names and their keywords.
    """
    return {
        "groups": list(KEYWORD_GROUPS.keys()),
        "details": {k: len(v) for k, v in KEYWORD_GROUPS.items()},
    }


def collect_by_topic(
    topic: str,
    platforms: List[Union[str, Tuple[str, str]]] = None,
    max_items: int = 50,
    global_filters: List[str] = None,
) -> Dict:
    """
    Collect news by predefined topic/keyword group.

    Uses TrendRadar-style word group matching for better accuracy.

    Args:
        topic: Topic name (e.g., "AI", "科技公司", "芯片半导体")
                Available topics: AI, 科技公司, 芯片半导体, 新能源, 机器人, 航天, 金融, 国际
        platforms: List of platform IDs (optional, uses all if None)
        max_items: Maximum items per platform
        global_filters: Global filter words to exclude

    Returns:
        Same as collect_news but filtered by topic keywords
    """
    # Find topic (case-insensitive)
    actual_topic = None
    for key in KEYWORD_GROUPS:
        if key.lower() == topic.lower() or key == topic:
            actual_topic = key
            break

    if not actual_topic:
        return {
            "success": False,
            "error": f"Unknown topic: {topic}. Available: {list(KEYWORD_GROUPS.keys())}",
            "timestamp": format_timestamp(),
            "platforms": {},
            "total_count": 0,
            "failed": [],
        }

    # Get pre-parsed keyword group
    parsed_keywords = _get_parsed_keyword_group(actual_topic)

    # Create a word group for matching
    word_groups = [{
        "required": [],
        "normal": parsed_keywords,
        "group_key": actual_topic,
        "display_name": actual_topic,
        "max_count": 0,
    }]

    # Use all platforms if not specified
    if platforms is None:
        platforms = list(PLATFORM_NAMES.keys())

    return collect_news(
        platforms=platforms,
        max_items=max_items,
        word_groups=word_groups,
        global_filters=global_filters,
    )


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
