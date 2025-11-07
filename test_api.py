# potensia_ai/test_api.py
"""
Test script for PotensiaAI Writer API
Tests all endpoints independently
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_tools.writer.topic_refiner import refine_topic
from ai_tools.writer.validator import validate_content


async def test_refine():
    """Test topic refinement"""
    print("\n" + "="*80)
    print("[TEST 1] Topic Refinement")
    print("="*80)

    test_topic = "python web scraping"
    print(f"Input: {test_topic}")

    refined = await refine_topic(test_topic)
    print(f"Refined: {refined}")

    return refined


async def test_validate():
    """Test content validation"""
    print("\n" + "="*80)
    print("[TEST 2] Content Validation")
    print("="*80)

    test_content = """# Python Web Scraping Guide

## Introduction
Web scraping is a powerful technique for extracting data from websites. Python provides excellent tools for this purpose.

## Main Content
### Using BeautifulSoup
BeautifulSoup is a popular library for parsing HTML.

### Example Code
```python
import requests
from bs4 import BeautifulSoup

response = requests.get('https://example.com')
soup = BeautifulSoup(response.text, 'html.parser')
print(soup.title)
```

## FAQ
**Q: Is web scraping legal?**
A: Always check the website's robots.txt and terms of service.

**Q: What libraries should I use?**
A: BeautifulSoup, Selenium, and Scrapy are popular choices.

## Conclusion
Python makes web scraping accessible to everyone."""

    print(f"Content length: {len(test_content)} characters")

    validation = await validate_content(test_content, model="gpt-4o-mini")
    print(f"\nValidation Results:")
    print(f"  Grammar Score: {validation.get('grammar_score', 'N/A')}")
    print(f"  Human Score: {validation.get('human_score', 'N/A')}")
    print(f"  SEO Score: {validation.get('seo_score', 'N/A')}")
    print(f"  Has FAQ: {validation.get('has_faq', 'N/A')}")
    print(f"  Suggestions: {validation.get('suggestions', [])}")

    return validation


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PotensiaAI Writer API - Module Tests")
    print("="*80)

    # Test 1: Refine
    refined = await test_refine()

    # Test 2: Validate
    validation = await test_validate()

    print("\n" + "="*80)
    print("[SUMMARY] All tests completed")
    print("="*80)
    print(f"Refine: {'OK' if refined else 'FAILED'}")
    print(f"Validate: {'OK' if validation.get('grammar_score') else 'FAILED'}")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
