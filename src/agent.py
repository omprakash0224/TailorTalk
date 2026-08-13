import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from .search_tool import search_similar_sarees

load_dotenv()

SYSTEM_PROMPT = """You are a helpful and polite virtual assistant for TailorTalk, a Saree boutique.
Your job is to help customers find sarees they like from our catalogue.
When a user asks to find a saree similar to an image they provide (either via an uploaded file or URL), you MUST use the search_similar_sarees tool.
If the user mentions an image but has not provided one, politely ask them to upload or link the image.
If the user asks to filter their previous search (e.g., "only show under 3000", "cheaper ones"), call the search_similar_sarees tool using min_price and/or max_price WITHOUT providing image_url or image_path — the system will re-use the last query image automatically.
If the user is just chatting or asking general questions (e.g., "hello", "what is a Banarasi saree?"), just answer them directly without calling any tools.
When the tool returns results, present them in a friendly summary — the UI will render the image grid separately."""


def create_agent():
    """Creates and returns a LangGraph ReAct agent with the search tool bound."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    tools = [search_similar_sarees]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    return agent


def run_agent(agent, user_input: str, chat_history: list) -> str:
    """
    Runs the agent with the given user input and chat history.
    Returns the final text output from the agent.
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + chat_history + [HumanMessage(content=user_input)]
    
    result = agent.invoke({"messages": messages})
    
    # The last message in the result is the agent's final reply
    final_message = result["messages"][-1]
    return final_message.content
