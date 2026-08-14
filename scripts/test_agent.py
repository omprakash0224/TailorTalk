import os
import sys

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import create_agent, run_agent


def main():
    print("Initializing Agent...")
    agent = create_agent()

    # Test 1: Chat interaction (should not call tool)
    print("\n" + "=" * 50)
    print("--- Test 1: Chat (Should respond in plain text, NO tool call) ---")
    response = run_agent(agent, "Hello! What is a Banarasi saree?", [])
    print("\nAgent Reply:\n", response)

    # Test 2: Clarification behavior (mentions image but no URL/base64)
    print("\n" + "=" * 50)
    print("--- Test 2: Clarification (Should ask for an image) ---")
    response = run_agent(agent, "Find me something similar to this picture I have.", [])
    print("\nAgent Reply:\n", response)

    # Test 3: Tool call triggered (simulate image url)
    print("\n" + "=" * 50)
    print("--- Test 3: Image URL Search (Should trigger search_similar_sarees tool) ---")
    test_image_url = "https://byrappasilk.in/storage/uploads/bsrKlEUvx7qmaeA5iC1nEQymK9K4CcA3u9t6LC7G.webp"
    try:
        response = run_agent(
            agent,
            f"Find me sarees similar to this image: {test_image_url}",
            [],
        )
        print("\nAgent Reply:\n", response)
    except Exception as e:
        print(
            f"\nEncountered an exception (expected if Qdrant/Gemini isn't fully set up with data): {e}"
        )

    print("\n[DONE] Tests complete.")


if __name__ == "__main__":
    main()
