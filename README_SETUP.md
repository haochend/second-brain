# Setup Instructions

## Quick Start

1. **Create and activate virtual environment:**
```bash
# Create venv
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Install Ollama and pull model:**
```bash
# Install Ollama from https://ollama.ai
# Then pull the model:
ollama pull llama3.2
```

4. **Run the system:**
```bash
# Test the pipeline
python test_pipeline.py

# Or use the CLI
python run.py --help

# Add your first memory
python run.py add "My first thought"
```

## Development Setup

For development with editable install:
```bash
# In activated venv
pip install -e .

# Now you can use 'memory' command directly
memory --help
memory add "Test thought"
```

## Troubleshooting

### PyAudio issues on macOS:
```bash
brew install portaudio
pip install --force-reinstall pyaudio
```

### PyAudio issues on Ubuntu/Debian:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

### Ollama not found:
- Make sure Ollama is running: `ollama serve`
- Check if model is downloaded: `ollama list`
- Pull model if needed: `ollama pull llama3.2`