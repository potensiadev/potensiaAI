# Test generator and save output to file
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from ai_tools.writer.generator import generate_content

async def test():
    test_topic = "생애최초 주택담보대출, 신청 자격과 한도·금리는?"

    print(f"\n{'='*60}")
    print(f"Testing Content Generator")
    print(f"{'='*60}\n")
    print(f"Input Topic: {test_topic}\n")

    try:
        result = await generate_content(test_topic)

        # Save to file
        output_file = "generated_content.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)

        print(f"\n{'='*60}")
        print(f"SUCCESS! Content saved to: {output_file}")
        print(f"{'='*60}\n")

        # Show preview
        print("Preview (first 500 characters):")
        print(result[:500])
        print("\n...")

    except Exception as e:
        print(f"\n[ERROR] Content generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
