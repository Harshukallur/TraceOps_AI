
import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"


def ask_local_llm(question: str) -> str:
    """Generate a complete, evidence-based answer using local Ollama."""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are TraceOps AI, a graph-powered incident "
                        "investigation assistant. Analyze only the supplied "
                        "evidence. Follow the requested report structure "
                        "and finish every section. Use concise Markdown "
                        "headings and bullet points. Never output raw JSON "
                        "when a readable explanation is requested. Never "
                        "invent facts, claim an outage is confirmed without "
                        "evidence, or claim to have executed remediation. "
                        "Always finish your answer with a complete sentence."
                    ),
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "num_predict": 700,
                "temperature": 0.2,
            },
        },
        timeout=(10, 300),
    )

    response.raise_for_status()

    data = response.json()
    message = data.get("message", {})
    answer = message.get("content", "").strip()

    if not answer:
        raise RuntimeError("Ollama returned an empty response.")

    return answer
