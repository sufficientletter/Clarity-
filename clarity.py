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


if __name__ == "__main__":
    cli()
