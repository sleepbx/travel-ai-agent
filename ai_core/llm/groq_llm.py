import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    return Groq(api_key=api_key)


def call_groq(prompt, system_prompt=None, model=None):
    client = get_groq_client()

    if model is None:
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    messages = []

    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=1024,
    )

    return response.choices[0].message.content


# ---------------- STREAMING ----------------
def call_groq_stream(prompt: str, model: str | None = None):
    """
    Generator that yields text chunks as the LLM streams output.
    """
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

    """
    Generator that yields text chunks as the LLM streams output.
    """
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
        if chunk.choices and chunk.choices[0].delta:
            content = chunk.choices[0].delta.get("content")
            if content:
                yield content
