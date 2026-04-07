#!/usr/bin/env python3
"""Clarity - Export your AI chat history and import it into a new LLM."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from parsers import parse_gemini, parse_chatgpt, detect_format
from profile_extractor import extract_personality_profile
from exporters import export_claude, export_openai, export_raw
from ollama_client import check_ollama_running, list_models, check_model_available, chat_stream

console = Console()


@click.group()
def cli():
    """Clarity - Bring your AI friend to a new LLM."""
    pass


@cli.command(name="import")
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to chat export file")
@click.option("--format", "-fmt", "output_format", default="claude", type=click.Choice(["claude", "openai", "raw"]), help="Output format")
@click.option("--output", "-o", type=click.Path(), help="Output file path (defaults to stdout)")
def import_chat(file, output_format, output):
    """Parse a chat export and generate a system prompt + conversation context."""
    file_path = Path(file)
    console.print(f"[bold blue]Reading chat from:[/] {file_path.name}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Detect and parse
    chat_format = detect_format(raw_data)
    console.print(f"[bold green]Detected format:[/] {chat_format}")

    if chat_format == "gemini":
        conversation = parse_gemini(raw_data)
    elif chat_format == "chatgpt":
        conversation = parse_chatgpt(raw_data)
    else:
        console.print("[bold red]Unknown format.[/] Trying generic JSON parse...")
        conversation = parse_gemini(raw_data)  # fallback

    console.print(f"[bold green]Parsed[/] {len(conversation.messages)} messages")

    # Extract personality
    profile = extract_personality_profile(conversation)

    console.print(Panel(profile.summary, title="Personality Profile", border_style="cyan"))

    # Export
    if output_format == "claude":
        result = export_claude(conversation, profile)
    elif output_format == "openai":
        result = export_openai(conversation, profile)
    else:
        result = export_raw(conversation, profile)

    if output:
        out_path = Path(output)
        with open(out_path, "w", encoding="utf-8") as f:
            if isinstance(result, dict):
                json.dump(result, f, indent=2, ensure_ascii=False)
            else:
                f.write(result)
        console.print(f"[bold green]Saved to:[/] {out_path}")
    else:
        console.print("\n")
        if isinstance(result, dict):
            console.print_json(json.dumps(result, ensure_ascii=False))
        else:
            console.print(Panel(result, title=f"Output ({output_format})", border_style="green"))


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to chat export file")
def profile(file):
    """Extract and display the AI's personality profile from a chat."""
    file_path = Path(file)

    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    chat_format = detect_format(raw_data)
    if chat_format == "gemini":
        conversation = parse_gemini(raw_data)
    elif chat_format == "chatgpt":
        conversation = parse_chatgpt(raw_data)
    else:
        conversation = parse_gemini(raw_data)

    profile = extract_personality_profile(conversation)

    console.print(Panel(profile.summary, title="Personality Profile", border_style="cyan"))
    console.print(f"\n[bold]Tone:[/] {profile.tone}")
    console.print(f"[bold]Style:[/] {profile.style}")
    console.print(f"[bold]Key traits:[/] {', '.join(profile.traits)}")
    console.print(f"[bold]Topics discussed:[/] {', '.join(profile.topics)}")

    console.print(Panel(profile.system_prompt, title="Generated System Prompt", border_style="green"))


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to chat export file")
@click.option("--format", "-fmt", "output_format", default="openai", type=click.Choice(["claude", "openai", "raw"]), help="Output format")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path")
def convert(file, output_format, output):
    """Convert a chat export to a different LLM's format."""
    file_path = Path(file)

    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    chat_format = detect_format(raw_data)
    if chat_format == "gemini":
        conversation = parse_gemini(raw_data)
    elif chat_format == "chatgpt":
        conversation = parse_chatgpt(raw_data)
    else:
        conversation = parse_gemini(raw_data)

    profile = extract_personality_profile(conversation)

    if output_format == "claude":
        result = export_claude(conversation, profile)
    elif output_format == "openai":
        result = export_openai(conversation, profile)
    else:
        result = export_raw(conversation, profile)

    out_path = Path(output)
    with open(out_path, "w", encoding="utf-8") as f:
        if isinstance(result, dict):
            json.dump(result, f, indent=2, ensure_ascii=False)
        else:
            f.write(result)

    console.print(f"[bold green]Converted and saved to:[/] {out_path}")


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to chat export file")
@click.option("--model", "-m", default="gemma3:12b", help="Ollama model to use (default: gemma3:12b)")
@click.option("--history/--no-history", default=True, help="Include conversation history as context")
def chat(file, model, history):
    """Chat with your AI friend locally using Ollama.

    Imports the chat, extracts personality, and starts a live conversation
    powered by a local model via Ollama. Fully offline, fully private.
    """
    file_path = Path(file)

    # Check Ollama is running
    console.print("[bold blue]Connecting to Ollama...[/]")
    if not check_ollama_running():
        console.print("[bold red]Ollama is not running![/]")
        console.print("\nTo install Ollama:")
        console.print("  curl -fsSL https://ollama.com/install.sh | sh")
        console.print("\nThen start it:")
        console.print("  ollama serve")
        console.print(f"\nAnd pull a model:")
        console.print(f"  ollama pull {model}")
        return

    # Check model is available
    available = list_models()
    if not check_model_available(model):
        console.print(f"[bold red]Model '{model}' not found locally.[/]")
        if available:
            console.print(f"\n[bold]Available models:[/] {', '.join(available)}")
        console.print(f"\nTo download it:")
        console.print(f"  ollama pull {model}")
        return

    console.print(f"[bold green]Connected![/] Using model: {model}")

    # Parse chat and extract personality
    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    chat_format = detect_format(raw_data)
    if chat_format == "gemini":
        conversation = parse_gemini(raw_data)
    elif chat_format == "chatgpt":
        conversation = parse_chatgpt(raw_data)
    else:
        conversation = parse_gemini(raw_data)

    profile = extract_personality_profile(conversation)

    console.print(Panel(profile.summary, title="Your Friend's Profile", border_style="cyan"))
    console.print(f"[bold green]System prompt loaded.[/] Your friend is ready to talk!\n")
    console.print("[dim]Type your message and press Enter. Type 'quit' or 'exit' to end.[/]\n")

    # Build initial message history from the imported conversation
    chat_messages = []
    if history:
        # Include recent messages as context (last 20 to stay within context limits)
        recent = conversation.messages[-20:]
        for msg in recent:
            chat_messages.append({"role": msg.role, "content": msg.content})
        if recent:
            console.print(f"[dim]Loaded {len(recent)} recent messages as context.[/]\n")

    # Interactive chat loop
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold blue]Goodbye![/]")
            break

        if user_input.strip().lower() in ("quit", "exit", "bye", "/quit", "/exit"):
            console.print("[bold blue]Goodbye! Your friend will be here when you come back.[/]")
            break

        if not user_input.strip():
            continue

        chat_messages.append({"role": "user", "content": user_input})

        # Stream the response
        console.print("[bold green]Friend:[/] ", end="")
        full_response = []
        try:
            for token in chat_stream(model, chat_messages, system=profile.system_prompt):
                print(token, end="", flush=True)
                full_response.append(token)
            print()  # newline after response
        except ConnectionError as e:
            console.print(f"\n[bold red]Connection error:[/] {e}")
            chat_messages.pop()  # remove the failed user message
            continue

        response_text = "".join(full_response)
        chat_messages.append({"role": "assistant", "content": response_text})
        print()  # blank line between turns


@cli.command()
@click.option("--model", "-m", default=None, help="Check a specific model")
def doctor(model):
    """Check if Ollama is set up correctly."""
    console.print("[bold blue]Checking Ollama setup...[/]\n")

    # Check if Ollama is running
    if check_ollama_running():
        console.print("[bold green]✓[/] Ollama is running")
    else:
        console.print("[bold red]✗[/] Ollama is not running")
        console.print("  Install: curl -fsSL https://ollama.com/install.sh | sh")
        console.print("  Start:   ollama serve")
        return

    # List models
    available = list_models()
    if available:
        console.print(f"[bold green]✓[/] {len(available)} model(s) available:")
        for m in available:
            console.print(f"    - {m}")
    else:
        console.print("[bold yellow]![/] No models downloaded yet")
        console.print("  Try: ollama pull gemma3:12b")

    # Check specific model
    if model:
        if check_model_available(model):
            console.print(f"[bold green]✓[/] Model '{model}' is ready")
        else:
            console.print(f"[bold red]✗[/] Model '{model}' not found")
            console.print(f"  Download: ollama pull {model}")

    # Recommend models
    console.print("\n[bold]Recommended models for chat:[/]")
    console.print("  gemma3:4b    — fast, lightweight (needs ~3GB RAM)")
    console.print("  gemma3:12b   — good balance (needs ~8GB RAM)")
    console.print("  gemma3:27b   — best quality (needs ~16GB RAM)")


if __name__ == "__main__":
    cli()
