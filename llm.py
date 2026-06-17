from langchain_ollama import ChatOllama


def get_llm() -> ChatOllama:
    return ChatOllama(
        model="deepseek-r1:8b",
        base_url="http://localhost:11434",
        num_ctx=16384,
    )
