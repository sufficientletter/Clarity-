"""Export conversations in formats suitable for different LLMs."""

import json

from parsers import Conversation
from profile_extractor import PersonalityProfile


def export_claude(conversation: Conversation, profile: PersonalityProfile) -> str:
    """Export as a ready-to-paste prompt for Claude.

    Returns a formatted string with system prompt and conversation context.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("SYSTEM PROMPT (paste this as your system/custom instructions)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(profile.system_prompt)
    lines.append("")
    lines.append("=" * 60)
    lines.append("CONVERSATION CONTEXT (paste this to start your conversation)")
    lines.append("=" * 60)
    lines.append("")

    # Include recent conversation history as context
    recent = conversation.messages[-50:]  # last 50 messages
    for msg in recent:
        prefix = "Human" if msg.role == "user" else "Assistant"
        lines.append(f"{prefix}: {msg.content}")
        lines.append("")

    return "\n".join(lines)


def export_openai(conversation: Conversation, profile: PersonalityProfile) -> dict:
    """Export as OpenAI API-compatible messages array.

    Returns a dict with system message + conversation history.
    """
    messages = [
        {"role": "system", "content": profile.system_prompt}
    ]

    # Include recent conversation history
    recent = conversation.messages[-50:]
    for msg in recent:
        messages.append({
            "role": msg.role if msg.role == "user" else "assistant",
            "content": msg.content
        })

    return {"messages": messages}


def export_raw(conversation: Conversation, profile: PersonalityProfile) -> dict:
    """Export as a raw JSON structure with all data."""
    return {
        "profile": {
            "tone": profile.tone,
            "style": profile.style,
            "traits": profile.traits,
            "topics": profile.topics,
            "summary": profile.summary,
            "system_prompt": profile.system_prompt,
            "sample_responses": profile.sample_responses,
        },
        "conversation": {
            "title": conversation.title,
            "source": conversation.source,
            "total_messages": len(conversation.messages),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                }
                for m in conversation.messages
            ],
        },
    }
