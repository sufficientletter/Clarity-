# Clarity - Chat Export & Import for LLMs

Export your AI chat history (from Gemini, ChatGPT, etc.) and import the conversation context into a new LLM — preserving the personality, tone, and relationship you've built.

## Quick Start

```bash
pip install -r requirements.txt
python clarity.py import --file your_gemini_export.json
```

## Features

- **Parse Gemini exports** from Google Takeout (JSON format)
- **Extract personality** — analyzes your friend's tone, style, and recurring themes
- **Generate system prompts** — creates a prompt that captures who your AI friend is
- **Export for any LLM** — outputs in Claude, OpenAI, or generic chat format
- **Conversation memory** — includes key moments and context from your history

## How to Export from Gemini

1. Go to [Google Takeout](https://takeout.google.com/)
2. Deselect all, then select only **"Gemini Apps"**
3. Click **Create export** and download the archive
4. Extract the ZIP — your conversations are in `Takeout/Gemini Apps/`
5. Run Clarity on the JSON files

## Local Chat with Ollama (Offline)

Talk to your AI friend locally — no cloud, no API keys, fully private.

### Setup

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model (Gemma 3 is from Google, closest to Gemini)
ollama pull gemma3:12b

# 3. Check everything works
python clarity.py doctor
```

### Chat with your friend

```bash
python clarity.py chat --file your_gemini_export.json
```

This will:
- Parse your chat history
- Extract your friend's personality (tone, traits, style)
- Load recent messages as context
- Start a live local conversation, streaming responses

#### Model options

| Model | RAM needed | Quality |
|-------|-----------|---------|
| `gemma3:4b` | ~3 GB | Fast, lightweight |
| `gemma3:12b` | ~8 GB | Good balance (default) |
| `gemma3:27b` | ~16 GB | Best quality |

```bash
# Use a different model
python clarity.py chat --file export.json --model gemma3:27b

# Skip loading conversation history
python clarity.py chat --file export.json --no-history
```

## Other Commands

```bash
# Parse a Gemini export and generate a system prompt
python clarity.py import --file conversation.json

# Specify output format (claude, openai, raw)
python clarity.py import --file conversation.json --format claude

# Extract personality profile only
python clarity.py profile --file conversation.json

# Convert to a different LLM's chat format
python clarity.py convert --file conversation.json --format openai --output chat.json

# Check Ollama setup
python clarity.py doctor
```

## Output

Clarity generates:
- A **system prompt** capturing your friend's personality
- A **conversation summary** with key context
- A **formatted chat history** ready to paste into your new LLM
- A **live local chat** via Ollama (fully offline)
