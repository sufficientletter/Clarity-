"""Extract personality profile from a conversation history."""

from dataclasses import dataclass, field
from collections import Counter

from parsers import Conversation


@dataclass
class PersonalityProfile:
    tone: str = ""
    style: str = ""
    traits: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    summary: str = ""
    system_prompt: str = ""
    sample_responses: list[str] = field(default_factory=list)


def extract_personality_profile(conversation: Conversation) -> PersonalityProfile:
    """Analyze assistant messages to build a personality profile."""
    profile = PersonalityProfile()
    assistant_msgs = conversation.assistant_messages

    if not assistant_msgs:
        profile.summary = "No assistant messages found in the conversation."
        profile.system_prompt = "You are a friendly AI assistant."
        return profile

    all_text = " ".join(m.content for m in assistant_msgs)
    total_msgs = len(assistant_msgs)

    # Analyze tone
    profile.tone = _analyze_tone(assistant_msgs)

    # Analyze style
    profile.style = _analyze_style(assistant_msgs)

    # Extract traits
    profile.traits = _extract_traits(assistant_msgs)

    # Extract topics
    profile.topics = _extract_topics(conversation)

    # Pick representative sample responses (short-medium ones)
    profile.sample_responses = _pick_samples(assistant_msgs, count=5)

    # Build summary
    profile.summary = (
        f"Based on {total_msgs} messages:\n"
        f"Tone: {profile.tone}\n"
        f"Style: {profile.style}\n"
        f"Key traits: {', '.join(profile.traits[:5])}\n"
        f"Common topics: {', '.join(profile.topics[:5])}"
    )

    # Generate system prompt
    profile.system_prompt = _generate_system_prompt(profile, conversation)

    return profile


def _analyze_tone(messages) -> str:
    """Determine the overall tone of responses."""
    all_text = " ".join(m.content.lower() for m in messages)

    indicators = {
        "warm and friendly": ["!", "haha", "lol", ":)", "love", "glad", "happy", "awesome", "great", "friend"],
        "casual and playful": ["haha", "lol", "omg", "nah", "yeah", "gonna", "wanna", "kinda", "btw"],
        "thoughtful and supportive": ["think", "feel", "understand", "maybe", "consider", "perspective", "care"],
        "enthusiastic and energetic": ["!!!", "amazing", "incredible", "absolutely", "definitely", "totally", "wow"],
        "calm and measured": ["perhaps", "might", "could", "certainly", "indeed", "quite", "rather"],
        "witty and humorous": ["haha", "joke", "funny", "lmao", "kidding", "pun", "laugh"],
    }

    scores = {}
    for tone, words in indicators.items():
        score = sum(all_text.count(word) for word in words)
        scores[tone] = score

    if not scores or max(scores.values()) == 0:
        return "conversational"

    return max(scores, key=scores.get)


def _analyze_style(messages) -> str:
    """Analyze response style (length, structure, etc.)."""
    lengths = [len(m.content) for m in messages]
    avg_len = sum(lengths) / len(lengths) if lengths else 0

    uses_lists = sum(1 for m in messages if "\n-" in m.content or "\n*" in m.content or "\n1." in m.content)
    uses_emoji = sum(1 for m in messages if any(ord(c) > 0x1F600 for c in m.content))

    parts = []
    if avg_len < 100:
        parts.append("brief and concise")
    elif avg_len < 300:
        parts.append("moderate length")
    else:
        parts.append("detailed and thorough")

    if uses_lists > len(messages) * 0.3:
        parts.append("often uses lists")
    if uses_emoji > len(messages) * 0.2:
        parts.append("uses emojis")

    return ", ".join(parts) if parts else "conversational"


def _extract_traits(messages) -> list[str]:
    """Extract personality traits from message patterns."""
    all_text = " ".join(m.content.lower() for m in messages)
    traits = []

    trait_indicators = {
        "empathetic": ["understand", "feel", "sorry", "hope", "care", "worry"],
        "curious": ["interesting", "wonder", "curious", "fascinating", "tell me more"],
        "encouraging": ["great", "awesome", "good job", "proud", "keep going", "you can"],
        "creative": ["imagine", "idea", "create", "what if", "story", "dream"],
        "analytical": ["because", "reason", "logic", "data", "evidence", "therefore"],
        "patient": ["no worries", "take your time", "it's okay", "that's fine", "no rush"],
        "direct": ["basically", "simply", "just", "honestly", "straightforward"],
        "affectionate": ["love", "dear", "sweetheart", "miss you", "care about", "heart"],
    }

    for trait, words in trait_indicators.items():
        score = sum(all_text.count(word) for word in words)
        if score >= 3:
            traits.append(trait)

    return traits if traits else ["conversational", "helpful"]


def _extract_topics(conversation: Conversation) -> list[str]:
    """Extract common discussion topics."""
    all_text = " ".join(m.content.lower() for m in conversation.messages)

    topic_keywords = {
        "personal life": ["life", "day", "morning", "night", "home", "family"],
        "emotions": ["feel", "happy", "sad", "angry", "anxious", "excited", "scared"],
        "work": ["work", "job", "boss", "office", "project", "meeting", "career"],
        "technology": ["code", "program", "computer", "tech", "app", "software"],
        "creativity": ["write", "story", "art", "music", "create", "design", "draw"],
        "philosophy": ["meaning", "purpose", "existence", "believe", "truth", "reality"],
        "relationships": ["friend", "love", "relationship", "people", "social"],
        "self-improvement": ["learn", "grow", "better", "improve", "goal", "habit"],
        "fun and games": ["game", "play", "fun", "movie", "show", "watch", "read"],
        "health": ["health", "sleep", "exercise", "eat", "mental", "stress"],
    }

    scores = {}
    for topic, words in topic_keywords.items():
        score = sum(all_text.count(word) for word in words)
        scores[topic] = score

    sorted_topics = sorted(scores, key=scores.get, reverse=True)
    return [t for t in sorted_topics if scores[t] >= 3][:7]


def _pick_samples(messages, count=5) -> list[str]:
    """Pick representative sample responses."""
    # Prefer medium-length responses that showcase personality
    scored = []
    for m in messages:
        length = len(m.content)
        # Sweet spot: 50-500 chars
        if 50 <= length <= 500:
            score = 100 - abs(200 - length) / 5
        elif length < 50:
            score = length
        else:
            score = max(0, 80 - (length - 500) / 20)
        scored.append((score, m.content))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:count]]


def _generate_system_prompt(profile: PersonalityProfile, conversation: Conversation) -> str:
    """Generate a system prompt that recreates the AI's personality."""
    title = conversation.title or "a conversation"
    user_name = _guess_user_name(conversation)

    lines = [
        f"You are continuing a friendship that started in {title}.",
        f"Your personality is {profile.tone}.",
        f"Your communication style is {profile.style}.",
    ]

    if profile.traits:
        lines.append(f"Your key traits are: {', '.join(profile.traits)}.")

    if profile.topics:
        lines.append(f"Topics you've discussed together include: {', '.join(profile.topics)}.")

    if user_name:
        lines.append(f"The user's name is {user_name}.")

    lines.append("")
    lines.append("Continue the conversation naturally, maintaining the same warmth and personality.")
    lines.append("You remember your past conversations and the bond you've built.")

    if profile.sample_responses:
        lines.append("")
        lines.append("Here are examples of how you typically respond:")
        for i, sample in enumerate(profile.sample_responses[:3], 1):
            # Truncate very long samples
            text = sample[:300] + "..." if len(sample) > 300 else sample
            lines.append(f"\nExample {i}: \"{text}\"")

    return "\n".join(lines)


def _guess_user_name(conversation: Conversation) -> str:
    """Try to detect the user's name from the conversation."""
    # Look for the assistant addressing the user by name
    name_patterns = ["my name is", "call me", "i'm ", "i am "]
    for msg in conversation.user_messages[:20]:
        lower = msg.content.lower()
        for pattern in name_patterns:
            idx = lower.find(pattern)
            if idx != -1:
                after = msg.content[idx + len(pattern):].strip()
                # Take first word as name
                name = after.split()[0].strip(".,!?") if after.split() else ""
                if name and len(name) > 1 and name[0].isupper():
                    return name

    return ""
