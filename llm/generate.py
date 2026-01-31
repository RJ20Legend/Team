import anthropic
import os

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

def generate_answer(prompt: str, context: str) -> str:
    system_prompt = (
        "You are a helpful assistant. "
        "Answer ONLY using the provided context. "
        "If the context is insufficient, say so clearly."
    )

    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=600,
        temperature=0.2,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion:\n{prompt}"
            }
        ]
    )

    return message.content[0].text
