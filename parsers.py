"""Parsers for different AI chat export formats."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    role: str          # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


@dataclass
class Conversation:
    messages: list[Message] = field(default_factory=list)
    title: Optional[str] = None
    source: str = "unknown"

    @property
    def assistant_messages(self) -> list[Message]:
        return [m for m in self.messages if m.role == "assistant"]

    @property
    def user_messages(self) -> list[Message]:
        return [m for m in self.messages if m.role == "user"]


def detect_format(data) -> str:
    """Detect the export format from the raw JSON data."""
    # Google Takeout / Gemini format
    if isinstance(data, dict):
        # Single Gemini conversation from Takeout
        if "conversation" in data:
            return "gemini"
        # Gemini format with entries at top level
        if any(key in data for key in ["entries", "messages", "turns"]):
            return "gemini"

    # ChatGPT export format (list of conversations)
    if isinstance(data, list):
        if len(data) > 0:
            first = data[0]
            if isinstance(first, dict):
                if "mapping" in first:
                    return "chatgpt"
                # Gemini Takeout sometimes exports as a list
                if "conversation" in first:
                    return "gemini"

    # Generic / unknown
    return "unknown"


def parse_gemini(data) -> Conversation:
    """Parse Google Gemini / Google Takeout export format.

    Gemini exports from Google Takeout have varied structures.
    This handles the common patterns.
    """
    conversation = Conversation(source="gemini")

    # Handle list of conversations — take the first or merge
    if isinstance(data, list):
        if len(data) == 0:
            return conversation
        # If it's a list of conversation objects, parse each
        for item in data:
            if isinstance(item, dict):
                sub = _parse_single_gemini(item)
                conversation.messages.extend(sub.messages)
                if sub.title and not conversation.title:
                    conversation.title = sub.title
        return conversation

    return _parse_single_gemini(data)


def _parse_single_gemini(data: dict) -> Conversation:
    """Parse a single Gemini conversation object."""
    conversation = Conversation(source="gemini")

    # Try to get title
    conversation.title = data.get("title") or data.get("name") or data.get("conversationTitle")

    # Pattern 1: "conversation" key with list of turns
    if "conversation" in data:
        turns = data["conversation"]
        if isinstance(turns, list):
            for turn in turns:
                _extract_gemini_turn(turn, conversation)
            return conversation

    # Pattern 2: "entries" or "messages" key
    for key in ["entries", "messages", "turns", "data"]:
        if key in data and isinstance(data[key], list):
            for entry in data[key]:
                _extract_gemini_turn(entry, conversation)
            return conversation

    # Pattern 3: flat structure with role/content pairs
    if "role" in data and ("content" in data or "text" in data or "parts" in data):
        _extract_gemini_turn(data, conversation)
        return conversation

    # Pattern 4: try all list values in the dict
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict) and any(k in value[0] for k in ["role", "author", "content"]):
                for entry in value:
                    _extract_gemini_turn(entry, conversation)
                if conversation.messages:
                    return conversation

    return conversation


def _extract_gemini_turn(turn: dict, conversation: Conversation):
    """Extract a single turn from a Gemini conversation entry."""
    if not isinstance(turn, dict):
        return

    # Determine role
    role_raw = turn.get("role") or turn.get("author") or turn.get("sender") or ""
    role_raw = role_raw.lower().strip()

    if role_raw in ("user", "human", "0"):
        role = "user"
    elif role_raw in ("model", "assistant", "bot", "gemini", "1"):
        role = "assistant"
    else:
        # Try to infer from other fields
        if turn.get("isUser") or turn.get("is_user"):
            role = "user"
        elif turn.get("isBot") or turn.get("is_bot") or turn.get("isModel"):
            role = "assistant"
        else:
            return  # skip unknown roles

    # Extract content
    content = _extract_content(turn)
    if not content:
        return

    timestamp = turn.get("timestamp") or turn.get("createTime") or turn.get("create_time")

    conversation.messages.append(Message(role=role, content=content, timestamp=timestamp))


def _extract_content(turn: dict) -> str:
    """Extract text content from a turn, handling various nested structures."""
    # Direct content field
    if "content" in turn:
        c = turn["content"]
        if isinstance(c, str):
            return c.strip()
        if isinstance(c, list):
            # List of parts
            parts = []
            for part in c:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    parts.append(part.get("text", "") or part.get("content", ""))
            return "\n".join(p for p in parts if p).strip()
        if isinstance(c, dict):
            return c.get("text", "") or c.get("content", "")

    # "text" field
    if "text" in turn:
        t = turn["text"]
        if isinstance(t, str):
            return t.strip()
        if isinstance(t, list):
            return "\n".join(str(x) for x in t).strip()

    # "parts" field (Gemini API style)
    if "parts" in turn:
        parts = turn["parts"]
        if isinstance(parts, list):
            texts = []
            for part in parts:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict):
                    texts.append(part.get("text", ""))
            return "\n".join(t for t in texts if t).strip()

    # "message" field
    if "message" in turn:
        m = turn["message"]
        if isinstance(m, str):
            return m.strip()
        if isinstance(m, dict):
            return _extract_content(m)

    return ""


def parse_chatgpt(data) -> Conversation:
    """Parse ChatGPT export format (from Settings > Export data)."""
    conversation = Conversation(source="chatgpt")

    if isinstance(data, list):
        # List of conversations — merge all or take first
        for conv_data in data:
            sub = _parse_single_chatgpt(conv_data)
            conversation.messages.extend(sub.messages)
            if sub.title and not conversation.title:
                conversation.title = sub.title
        return conversation

    return _parse_single_chatgpt(data)


def _parse_single_chatgpt(data: dict) -> Conversation:
    """Parse a single ChatGPT conversation."""
    conversation = Conversation(source="chatgpt")
    conversation.title = data.get("title")

    mapping = data.get("mapping", {})
    if not mapping:
        return conversation

    # Build ordered message list from the mapping tree
    nodes = []
    for node_id, node in mapping.items():
        msg = node.get("message")
        if not msg:
            continue
        role = msg.get("author", {}).get("role", "")
        if role not in ("user", "assistant"):
            continue

        content_obj = msg.get("content", {})
        parts = content_obj.get("parts", [])
        text_parts = [str(p) for p in parts if isinstance(p, str)]
        content = "\n".join(text_parts).strip()

        if not content:
            continue

        timestamp = msg.get("create_time")
        nodes.append((timestamp or 0, Message(role=role, content=content, timestamp=str(timestamp) if timestamp else None)))

    # Sort by timestamp
    nodes.sort(key=lambda x: x[0])
    conversation.messages = [msg for _, msg in nodes]

    return conversation
