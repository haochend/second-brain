from setuptools import setup, find_packages

setup(
    name="second-brain",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "openai-whisper",
        "ollama",
        "pyaudio",
        "click",
        "rich",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "memory=memory.cli.commands:cli",
        ],
    },
    python_requires=">=3.9",
)