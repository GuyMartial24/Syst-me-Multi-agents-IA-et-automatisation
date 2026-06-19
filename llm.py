from crewai import LLM


def get_llm():
    return LLM(
        model="ollama/llama3.1",
        base_url="http://localhost:11434",
        temperature=0,
        timeout=120
    )
