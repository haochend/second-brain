# Second Brain 🧠

A unified memory system that captures all your thoughts through voice and text, understands them automatically, and surfaces them when you need them.

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
ollama pull llama3.2

# Run the CLI
python run.py --help

# Or install in development mode
pip install -e .
memory --help

# Start capturing thoughts
python run.py add "Just had a great idea about the new feature"

# Search your memories
python run.py search "ideas from yesterday"
python run.py tasks  # Show all tasks
python run.py today  # Today's timeline
```

## Key Features

### 🎤 Frictionless Capture
- Global hotkey for instant voice capture
- Voice activity detection - just speak and go
- Text input via CLI or system tray
- No categorization needed - just think out loud

### 🧠 Intelligent Processing
- Local transcription with Whisper
- Automatic extraction of:
  - Tasks and action items
  - People, projects, and topics
  - Dates and deadlines
  - Ideas and observations
  - Questions and decisions
  - Emotional context and energy levels

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
- 8GB RAM (16GB recommended)
- 20GB free disk space
- macOS, Linux, or Windows (WSL2)

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

3. **Set up Whisper and Ollama:**
   ```bash
   # Whisper will download on first use
   # Install Ollama from https://ollama.ai
   ollama pull llama3.2
   ```

4. **Initialize the database:**
   ```bash
   python -m memory.cli init
   ```

## Usage

### Capturing Thoughts

```bash
# Voice capture (default)
memory add

# Text capture
memory add "Remember to review the pull request"

# With metadata
memory add "Meeting with Sarah about auth" --project authsystem
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
2. **Processing Pipeline**: Background transcription and extraction
3. **Storage Layer**: SQLite for data, Qdrant for vectors
4. **Access Layer**: CLI, MCP server, and future web UI

See `docs/unified_memory_design.md` for detailed architecture.

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

- [x] Core capture and processing pipeline
- [x] Voice transcription with Whisper
- [x] LLM extraction with Ollama
- [ ] Semantic search with vectors
- [ ] MCP server for AI tools
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