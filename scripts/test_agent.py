import os
import sys
import base64

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import create_agent

def main():
    print("Initializing Agent...")
    agent_executor = create_agent()
    
    # Test 1: Chat interaction (should not call tool)
    print("\n" + "="*50)
    print("--- Test 1: Chat (Should respond in plain text, NO tool call) ---")
    response = agent_executor.invoke({"input": "Hello! What is a Banarasi saree?"})
    print("\nAgent Reply:\n", response["output"])
    
    # Test 2: Clarification behavior (mentions image but no URL/base64)
    print("\n" + "="*50)
    print("--- Test 2: Clarification (Should ask for an image) ---")
    response = agent_executor.invoke({"input": "Find me something similar to this picture I have."})
    print("\nAgent Reply:\n", response["output"])
    
    # Test 3: Tool call triggered (simulate image url)
    print("\n" + "="*50)
    print("--- Test 3: Image URL Search (Should trigger search_similar_sarees tool) ---")
    # For testing, we use a placeholder image URL
    test_image_url = "https://via.placeholder.com/150/0000FF/808080.png?text=Saree"
    try:
        response = agent_executor.invoke({"input": f"Find me sarees similar to this image: {test_image_url}"})
        print("\nAgent Reply:\n", response["output"])
    except Exception as e:
        print(f"\nEncountered an exception (expected if Qdrant/Gemini isn't fully set up with data): {e}")
    
    print("\n✅ Tests complete.")

if __name__ == "__main__":
    main()
