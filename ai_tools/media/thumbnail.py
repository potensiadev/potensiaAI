# potensia_ai/ai_tools/media/thumbnail.py
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from openai import AsyncOpenAI
from core.config import settings

# Configure logging
logger = logging.getLogger("media.thumbnail")

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_thumbnail(prompt: str, size: str = "1024x1024") -> Dict:
    """
    Generate a thumbnail image using OpenAI DALL-E based on a text prompt.

    This function creates an AI-generated image suitable for blog thumbnails,
    article headers, or social media previews. It uses OpenAI's DALL-E model
    to generate visually appealing images from text descriptions.

    Args:
        prompt: Text description of the desired image (e.g., "modern illustration of a car")
        size: Image resolution in format "WIDTHxHEIGHT".
              Supported sizes for DALL-E 3: "1024x1024", "1792x1024", "1024x1792"
              Supported sizes for DALL-E 2: "256x256", "512x512", "1024x1024"
              Default: "1024x1024"

    Returns:
        dict: Dictionary containing:
            - url (str): Direct URL to the generated image
            - prompt_used (str): The actual prompt sent to the API
            - size (str): The image dimensions used
            - revised_prompt (str, optional): DALL-E's revised version of the prompt

        On error, returns:
            - error (str): Error message
            - prompt_used (str): The prompt that was attempted

    Raises:
        No exceptions raised; errors are caught and returned in the response dict

    Example:
        >>> result = await generate_thumbnail("winter landscape with mountains", "1024x1024")
        >>> print(result["url"])
        https://oaidalleapiprodscus.blob.core.windows.net/private/...
    """
    logger.info(f"[{datetime.now()}] [MEDIA] [START] Generating thumbnail for: {prompt[:100]}")

    try:
        # Validate size format
        valid_sizes_dalle3 = ["1024x1024", "1792x1024", "1024x1792"]
        valid_sizes_dalle2 = ["256x256", "512x512", "1024x1024"]

        if size not in valid_sizes_dalle3 and size not in valid_sizes_dalle2:
            logger.warning(f"Invalid size '{size}', defaulting to 1024x1024")
            size = "1024x1024"

        # Determine which model to use based on size
        # DALL-E 3 supports higher resolutions and better quality
        if size in ["1792x1024", "1024x1792"]:
            model = "dall-e-3"
        else:
            # Use DALL-E 3 for better quality (can fallback to dall-e-2 if needed)
            model = "dall-e-3"

        logger.info(f"[{datetime.now()}] [MEDIA] Using model: {model}, size: {size}")

        # Call OpenAI Image Generation API
        response = await openai_client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality="standard",  # "standard" or "hd" (hd costs more)
            n=1,  # Number of images to generate
        )

        # Extract image URL from response
        image_url = response.data[0].url
        revised_prompt = getattr(response.data[0], 'revised_prompt', None)

        logger.info(f"[{datetime.now()}] [MEDIA] [SUCCESS] Image generated: {image_url[:80]}...")

        result = {
            "url": image_url,
            "prompt_used": prompt,
            "size": size,
        }

        # DALL-E 3 often provides a revised prompt
        if revised_prompt:
            result["revised_prompt"] = revised_prompt
            logger.info(f"[{datetime.now()}] [MEDIA] Revised prompt: {revised_prompt[:100]}...")

        return result

    except Exception as e:
        error_msg = f"Failed to generate thumbnail: {str(e)}"
        logger.error(f"[{datetime.now()}] [MEDIA] [ERROR] {error_msg}")
        logger.exception("Thumbnail generation error details")

        return {
            "error": error_msg,
            "prompt_used": prompt,
            "size": size
        }


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

    async def main():
        """Test thumbnail generation with sample prompts"""
        test_prompts = [
            ("운전면허 갱신 과태료, 현대적인 일러스트", "1024x1024"),
            ("겨울철 싱크대 냄새 제거, 깔끔한 주방 이미지", "1024x1024"),
            ("Python web scraping tutorial, modern tech illustration", "1024x1024"),
        ]

        print("\n" + "="*80)
        print("Thumbnail Generator Test")
        print("="*80 + "\n")

        for prompt, size in test_prompts:
            print(f"\nPrompt: {prompt}")
            print(f"Size: {size}")
            print("-" * 80)

            try:
                result = await generate_thumbnail(prompt, size)

                if "error" in result:
                    print(f"❌ ERROR: {result['error']}")
                else:
                    print(f"✅ SUCCESS!")
                    print(f"   URL: {result['url']}")
                    print(f"   Size: {result['size']}")
                    if "revised_prompt" in result:
                        print(f"   Revised Prompt: {result['revised_prompt'][:100]}...")

                # Add delay to avoid rate limiting
                print("\nWaiting 5 seconds before next request...")
                await asyncio.sleep(5)

            except Exception as e:
                print(f"❌ EXCEPTION: {str(e)}")
                logger.exception("Test failed")

        print("\n" + "="*80)
        print("Test Complete")
        print("="*80 + "\n")

    asyncio.run(main())
