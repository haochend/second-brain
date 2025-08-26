# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Second Brain** - A unified memory system that captures thoughts through voice/text and intelligently surfaces them when needed.

## Core Concept

Unlike traditional note apps that force categorization at input, this system:
- Accepts all thoughts naturally (voice or text)
- Automatically extracts meaning (tasks, ideas, decisions, questions, etc.)
- Provides different views based on what you need
- Runs entirely locally for privacy

## Architecture

```
Input (voice/text) → Queue → Processing (transcribe/extract) → Storage → Query/Views
                                                                          ↓
                                                                     MCP Server (AI tools)
```

## Tech Stack

- **Language**: Python 3.9+
- **Transcription**: OpenAI Whisper (local)
- **LLM**: Ollama with Llama 3.2 (local)
- **Database**: SQLite + Qdrant (vector search)
- **CLI**: Click
- **API**: FastAPI (for MCP server)

## Project Structure

```
src/memory/
├── capture/     # Voice recording, text input, queue
├── processing/  # Transcription, extraction, enrichment
├── storage/     # Database, vector store, models
├── query/       # Search, views, filters
├── integration/ # MCP server, export
└── cli/         # Command interface
```

## Key Commands

```bash
# Development
pip install -r requirements.txt
python -m memory.cli

# Testing
pytest tests/

# Common operations
memory add              # Voice capture
memory add "text"       # Text capture
memory search "query"   # Search memories
memory tasks            # Show tasks view
```

## Current Implementation Status

Check `docs/unified_memory_design.md` for the full design and implementation roadmap.

## Development Focus

When implementing features:
1. Start with the simplest working version
2. Voice capture and queue should be instant (<2 sec)
3. Processing can happen in background (5-10 min is fine)
4. Extraction accuracy > speed (we're not real-time constrained)
5. Local-only - no cloud services

## Key Design Decisions

- **Queue-based**: Capture is instant, processing is async
- **Gentle extraction**: Don't force structure where it doesn't exist
- **Local-first**: Everything runs on user's machine
- **Flexible schema**: JSON fields for extracted data
- **Multiple views**: Same data, different lenses (tasks, daily notes, projects, etc.)