# Second Brain 🧠

A unified memory system that captures all your thoughts through voice and text, understands them automatically, and surfaces them when you need them.

**Status**: Working implementation with voice capture, MLX Whisper transcription, and LLM extraction

## What is this?

Second Brain is a local-first memory augmentation system that:
- **Captures everything** - Voice notes, text thoughts, ideas, tasks, questions - without forcing you to categorize
- **Understands naturally** - Automatically extracts tasks, deadlines, people, topics, and context
- **Surfaces intelligently** - Different views for different needs (task list, daily notes, project overviews)
- **Respects privacy** - Everything runs locally on your machine

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install system dependencies (macOS)
brew install portaudio  # Required for PyAudio

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set up local models (one-time)
# Install Ollama: https://ollama.ai
ollama pull gpt-oss:120b  # Or any other model you prefer

# Run the CLI
python run.py --help

# Or install in development mode
pip install -e .
memory --help

# Start capturing thoughts
python run.py add "Just had a great idea about the new feature"  # Text input
python run.py add -v  # Voice capture (press Enter to start/stop)

# Search your memories
python run.py search "ideas from yesterday"
python run.py tasks  # Show all tasks
python run.py today  # Today's timeline
python run.py process  # Process pending memories
```

## Key Features

### 🎤 Frictionless Capture
- Global hotkey for instant voice capture
- Voice activity detection - just speak and go
- Text input via CLI or system tray
- No categorization needed - just think out loud

### 🧠 Intelligent Processing
- Local transcription with MLX Whisper (GPU-accelerated on Apple Silicon)
- Automatic extraction with LLM (Ollama) of:
  - Tasks and action items with priorities
  - People, projects, and topics
  - Dates and deadlines
  - Ideas and observations
  - Questions and decisions
  - Emotional context and mood

### 🔍 Smart Retrieval
- Natural language search
- Multiple view types:
  - Task management view
  - Daily notes / journal
  - Project overviews
  - Person interaction history
- Automatic relationship detection between thoughts

### 🤖 AI Integration
- MCP (Model Context Protocol) server
- Automatic context injection for AI tools
- Works with Claude, Cursor, and other MCP-compatible tools

### 🔒 Privacy First
- 100% local processing
- No cloud services required
- Your thoughts stay on your machine
- Optional encryption at rest

## Installation

### Requirements
- Python 3.9+
- 8GB RAM (16GB recommended for large LLMs)
- 5GB free disk space (+ model storage)
- macOS (Apple Silicon recommended), Linux, or Windows (WSL2)
- Ollama for LLM extraction
- PortAudio for voice capture

### Setup

1. **Install system dependencies:**
   ```bash
   # macOS
   brew install portaudio
   
   # Ubuntu/Debian
   sudo apt-get install portaudio19-dev
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up models:**
   ```bash
   # MLX Whisper models download automatically on first use
   # For Apple Silicon, MLX provides GPU acceleration
   
   # Install Ollama from https://ollama.ai
   ollama pull gpt-oss:120b  # Or smaller models like llama3.2
   ```

4. **Initialize the database:**
   ```bash
   python -m memory.cli init
   ```

## Usage

### Capturing Thoughts

```bash
# Voice capture (press Enter to start, Enter again to stop)
python run.py add -v
# or just: memory add -v

# Text capture
python run.py add "Remember to review the pull request"

# Interactive text (multi-line, Ctrl+D to finish)
python run.py add
```

### Searching and Viewing

```bash
# Natural language search
memory search "decisions about the API design"

# View tasks
memory tasks
memory tasks --pending
memory tasks --project authsystem

# Daily notes
memory today
memory yesterday
memory date 2024-01-15

# Project overview
memory project authsystem
```

### Processing

```bash
# Check processing status
memory status

# Force immediate processing
memory process --now

# Review and correct extractions
memory review
```

## Architecture

The system uses a queue-based architecture for instant capture and background processing:

1. **Capture Layer**: Instant save to queue (<2 seconds)
   - Voice: PyAudio → WAV file → Queue
   - Text: Direct to Queue
2. **Processing Pipeline**: Background transcription and extraction
   - Voice: MLX Whisper (GPU) → Text
   - Text: Ollama LLM → Structured extraction
3. **Storage Layer**: SQLite with FTS5 for full-text search
   - Manual FTS management (no triggers) for reliability
4. **Access Layer**: CLI with Rich formatting

See `docs/unified_memory_design.md` for detailed architecture and `CLAUDE.md` for implementation details.

## Development

```bash
# Run tests
pytest tests/

# Run with debug logging
memory --debug add

# Development mode
pip install -r requirements-dev.txt
python -m memory.cli --dev
```

## Roadmap

### Completed ✅
- [x] Core capture and processing pipeline
- [x] Voice transcription with MLX Whisper (GPU-accelerated)
- [x] LLM extraction with Ollama
- [x] Full-text search with SQLite FTS5
- [x] Queue-based async processing
- [x] Database with retry logic and concurrency handling

### In Progress 🚧
- [ ] Semantic search with vectors
- [ ] MCP server for AI tools

### Planned 📋
- [ ] System tray application
- [ ] Web interface
- [ ] Mobile apps
- [ ] Cloud sync (optional)

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit PRs.

## License

MIT - See LICENSE file

## Acknowledgments

Built with:
- [Whisper](https://github.com/openai/whisper) for transcription
- [Ollama](https://ollama.ai) for local LLM
- [Qdrant](https://qdrant.tech) for vector search
- [MCP](https://modelcontextprotocol.io) for AI integration

---

*Your thoughts, understood and remembered.*