from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def pick_llm(level: str):
    """
    Returns an appropriate Gemini model based on the task difficulty.

    Levels:
        low    -> gemini-3.8-flash-lite
        medium -> gemini-3.8-flash
        high   -> gemini-3.8-pro
    """

    level = level.lower()

    if level == "low":
        model = "gemini-3.1-flash-lite"

    elif level == "medium":
        model = "gemini-3.5-flash-lite"

    elif level == "high":
        model = "gemini-3.8-flash"

    else:
        raise ValueError(f"Unsupported level: {level}")

    return ChatGoogleGenerativeAI(
        model=model,
        temperature=0,
        # Bound each upstream request. The integration otherwise retries
        # transient Gemini failures many times, which can keep a graph node
        # blocked long enough for the web client's request to time out.
        request_timeout=60,
        retries=2,
    )


if __name__ == "__main__":
    llm = pick_llm("medium")

    print("Starting LLM...")
    response = llm.invoke("What is the capital of India?")

    print(response.content)
