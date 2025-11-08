# potensia_ai/ai_tools/keyword/analyzer.py
import asyncio
import logging
import random
import json
import re
from typing import List, Dict
from openai import AsyncOpenAI
from core.config import settings

# Configure logging
logger = logging.getLogger("keyword.analyzer")

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# System prompt for keyword extraction
KEYWORD_EXTRACTION_PROMPT = """You are an SEO keyword research expert specializing in Korean and English markets.

Your task is to analyze a given blog topic and extract relevant SEO keywords with the following characteristics:
1. Primary keywords (high search volume, moderate competition)
2. Long-tail keywords (specific phrases, lower competition)
3. Related semantic keywords
4. Question-based keywords

For each keyword, provide:
- The keyword phrase
- Estimated search volume (realistic numbers)
- Competition level (0.0 to 1.0, where 1.0 is highest)
- SEO difficulty (0.0 to 1.0, where 1.0 is hardest to rank)

Return ONLY a valid JSON array with this exact structure:
[
  {
    "keyword": "keyword phrase",
    "search_volume": 15000,
    "competition": 0.45,
    "difficulty": 0.6,
    "type": "primary|long-tail|semantic|question"
  }
]

IMPORTANT:
- Return 10-20 keywords
- Mix different types (primary, long-tail, semantic, question)
- Use realistic search volumes (100-100000 range)
- Competition and difficulty should be between 0.0 and 1.0
- NO explanations, NO markdown, ONLY the JSON array"""


def calculate_estimated_metrics(keyword: str, topic: str) -> Dict[str, float]:
    """
    Calculate estimated metrics for a keyword based on heuristics.
    This is a fallback when real API data is unavailable.

    Args:
        keyword: The keyword phrase
        topic: Original topic for context

    Returns:
        dict: Estimated search_volume, competition, difficulty
    """
    # Simple heuristics based on keyword length and characteristics
    word_count = len(keyword.split())

    # Longer phrases (long-tail) typically have lower volume but lower competition
    if word_count >= 4:
        search_volume = random.randint(100, 2000)
        competition = random.uniform(0.1, 0.4)
        difficulty = random.uniform(0.2, 0.5)
    elif word_count == 3:
        search_volume = random.randint(1000, 10000)
        competition = random.uniform(0.3, 0.6)
        difficulty = random.uniform(0.4, 0.7)
    else:  # 1-2 words
        search_volume = random.randint(5000, 50000)
        competition = random.uniform(0.5, 0.9)
        difficulty = random.uniform(0.6, 0.9)

    # Question keywords typically have moderate volume
    if keyword.startswith(("어떻게", "왜", "무엇", "how", "why", "what", "when")):
        search_volume = random.randint(500, 5000)
        competition = random.uniform(0.2, 0.5)
        difficulty = random.uniform(0.3, 0.6)

    return {
        "search_volume": search_volume,
        "competition": round(competition, 2),
        "difficulty": round(difficulty, 2)
    }


async def analyze_keywords(topic: str, max_results: int = 10) -> List[Dict]:
    """
    Analyze a blog topic and extract SEO/AEO optimized keywords.

    This function uses OpenAI's API to generate relevant keywords based on the topic,
    then enriches them with estimated search volume, competition, and difficulty metrics.

    Args:
        topic: The blog topic or refined title to analyze
        max_results: Maximum number of keywords to return (default: 10)

    Returns:
        List[Dict]: List of keyword dictionaries sorted by search volume descending.
        Each dict contains:
            - keyword: str (the keyword phrase)
            - search_volume: int (estimated monthly searches)
            - competition: float (0.0-1.0, advertising competition)
            - difficulty: float (0.0-1.0, SEO ranking difficulty)
            - type: str (primary|long-tail|semantic|question)

    Raises:
        Exception: If OpenAI API call fails after retries

    Example:
        >>> keywords = await analyze_keywords("파이썬 웹 크롤링", max_results=5)
        >>> print(keywords[0])
        {
            "keyword": "파이썬 크롤링",
            "search_volume": 15000,
            "competition": 0.65,
            "difficulty": 0.72,
            "type": "primary"
        }
    """
    logger.info(f"Starting keyword analysis for topic: {topic[:50]}...")

    # Build user prompt with topic
    user_prompt = f"""Topic: {topic}

Extract SEO keywords for this topic. Focus on:
1. Main keywords that best represent this topic
2. Long-tail variations with specific intent
3. Related semantic keywords
4. Common questions people search

Return the JSON array with 10-20 keywords."""

    # Retry logic with exponential backoff
    for attempt in range(settings.MAX_RETRIES):
        try:
            logger.info(f"OpenAI API call attempt {attempt + 1}/{settings.MAX_RETRIES}")

            # Determine if this is a reasoning model
            model_name_lower = settings.MODEL_PRIMARY.lower()
            is_reasoning = any(keyword in model_name_lower
                             for keyword in ["o1-", "o3-", "gpt-5"])

            # Build API parameters
            api_params = {
                "model": settings.MODEL_PRIMARY,
                "messages": [
                    {"role": "system", "content": KEYWORD_EXTRACTION_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
            }

            # Reasoning models use max_completion_tokens
            if is_reasoning:
                api_params["max_completion_tokens"] = 2000
            else:
                api_params["max_tokens"] = 2000
                api_params["temperature"] = 0.3  # Lower temp for more consistent output

            response = await openai_client.chat.completions.create(**api_params)

            # Debug: Check response structure
            message_content = response.choices[0].message.content
            if message_content:
                content = message_content.strip()
            else:
                content = ""

            logger.info(f"Response content length: {len(content)} chars")

            if not content:
                logger.warning(f"Empty response from OpenAI (attempt {attempt + 1})")
                # Log finish reason for debugging
                finish_reason = response.choices[0].finish_reason
                logger.warning(f"Finish reason: {finish_reason}")

                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = min(settings.BACKOFF_MIN * (2 ** attempt), settings.BACKOFF_MAX)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ValueError("Empty response from OpenAI after all retries")

            # Parse JSON response

            # Extract JSON array from response (handle markdown code blocks)
            json_match = re.search(r'\[[\s\S]*\]', content)
            if not json_match:
                logger.error(f"No JSON array found in response: {content[:200]}")
                raise ValueError("Invalid response format from OpenAI")

            keywords_data = json.loads(json_match.group())

            if not isinstance(keywords_data, list) or len(keywords_data) == 0:
                logger.warning("Parsed data is not a valid list or is empty")
                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = min(settings.BACKOFF_MIN * (2 ** attempt), settings.BACKOFF_MAX)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ValueError("Invalid keyword data structure")

            # Validate and enrich keyword data
            enriched_keywords = []
            for kw in keywords_data:
                if not isinstance(kw, dict) or "keyword" not in kw:
                    logger.warning(f"Skipping invalid keyword entry: {kw}")
                    continue

                # Ensure all required fields exist
                keyword_entry = {
                    "keyword": kw.get("keyword", "").strip(),
                    "search_volume": kw.get("search_volume", 1000),
                    "competition": round(kw.get("competition", 0.5), 2),
                    "difficulty": round(kw.get("difficulty", 0.5), 2),
                    "type": kw.get("type", "primary")
                }

                # Validate numeric fields
                keyword_entry["search_volume"] = max(0, int(keyword_entry["search_volume"]))
                keyword_entry["competition"] = max(0.0, min(1.0, float(keyword_entry["competition"])))
                keyword_entry["difficulty"] = max(0.0, min(1.0, float(keyword_entry["difficulty"])))

                if keyword_entry["keyword"]:
                    enriched_keywords.append(keyword_entry)

            # Sort by search volume descending
            enriched_keywords.sort(key=lambda x: x["search_volume"], reverse=True)

            # Limit to max_results
            result = enriched_keywords[:max_results]

            logger.info(f"Successfully extracted {len(result)} keywords")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed (attempt {attempt + 1}): {str(e)}")
            if attempt < settings.MAX_RETRIES - 1:
                wait_time = min(settings.BACKOFF_MIN * (2 ** attempt), settings.BACKOFF_MAX)
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                # Fallback: generate keywords using heuristics
                logger.warning("Falling back to heuristic keyword generation")
                return generate_fallback_keywords(topic, max_results)

        except Exception as e:
            logger.error(f"Keyword analysis failed (attempt {attempt + 1}): {str(e)}")
            if attempt < settings.MAX_RETRIES - 1:
                wait_time = min(settings.BACKOFF_MIN * (2 ** attempt), settings.BACKOFF_MAX)
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error("All retry attempts failed, using fallback")
                return generate_fallback_keywords(topic, max_results)

    # Should not reach here, but just in case
    return generate_fallback_keywords(topic, max_results)


def generate_fallback_keywords(topic: str, max_results: int = 10) -> List[Dict]:
    """
    Generate fallback keywords using simple heuristics when API fails.

    Args:
        topic: The blog topic
        max_results: Maximum number of keywords to generate

    Returns:
        List[Dict]: List of generated keywords with estimated metrics
    """
    logger.info(f"Generating fallback keywords for: {topic[:50]}")

    # Extract main words from topic
    words = topic.split()

    # Generate basic keyword variations
    keywords = []

    # Add the topic itself
    keywords.append({
        "keyword": topic,
        "search_volume": random.randint(5000, 20000),
        "competition": 0.6,
        "difficulty": 0.7,
        "type": "primary"
    })

    # Add shorter variations (take first 2-3 words)
    if len(words) >= 2:
        short_kw = " ".join(words[:2])
        keywords.append({
            "keyword": short_kw,
            "search_volume": random.randint(10000, 50000),
            "competition": 0.75,
            "difficulty": 0.8,
            "type": "primary"
        })

    # Add long-tail variations
    long_tail_prefixes = ["어떻게", "방법", "가이드", "튜토리얼"]
    for prefix in long_tail_prefixes[:min(3, max_results - len(keywords))]:
        keywords.append({
            "keyword": f"{prefix} {topic}",
            "search_volume": random.randint(500, 3000),
            "competition": 0.3,
            "difficulty": 0.4,
            "type": "long-tail"
        })

    # Fill remaining with variations
    while len(keywords) < max_results:
        # Generate random variations
        if random.random() > 0.5 and len(words) >= 2:
            variation = " ".join(random.sample(words, min(len(words), 2)))
        else:
            variation = f"{topic} 예제"

        keywords.append({
            "keyword": variation,
            "search_volume": random.randint(1000, 10000),
            "competition": random.uniform(0.3, 0.7),
            "difficulty": random.uniform(0.4, 0.7),
            "type": "semantic"
        })

    # Sort by search volume and limit
    keywords.sort(key=lambda x: x["search_volume"], reverse=True)
    return keywords[:max_results]


# ============================================================
# Standalone Test
# ============================================================
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Configure logging for test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test():
        test_topics = [
            "파이썬 웹 크롤링",
            "생애최초 주택담보대출",
            "목동 영어유치원"
        ]

        print("\n" + "="*80)
        print("Keyword Analyzer Test")
        print("="*80 + "\n")

        for topic in test_topics:
            print(f"\nTopic: {topic}")
            print("-" * 80)

            try:
                keywords = await analyze_keywords(topic, max_results=5)

                print(f"Found {len(keywords)} keywords:\n")
                for i, kw in enumerate(keywords, 1):
                    print(f"{i}. {kw['keyword']}")
                    print(f"   Volume: {kw['search_volume']:,} | "
                          f"Competition: {kw['competition']:.2f} | "
                          f"Difficulty: {kw['difficulty']:.2f} | "
                          f"Type: {kw['type']}")

            except Exception as e:
                print(f"ERROR: {str(e)}")
                logger.exception("Test failed")

    asyncio.run(test())
