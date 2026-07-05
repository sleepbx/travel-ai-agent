import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def call_groq(prompt: str, system_prompt: str | None = None, model: str | None = None) -> str:
    client = get_groq_client()
    model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def call_groq_stream(prompt: str, model: str | None = None):
    """Generator that yields text chunks as the LLM streams output."""
    client = get_groq_client()
    model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=2048,
        stream=True,
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and hasattr(delta, "content") and delta.content:
            yield delta.content
