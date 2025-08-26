#!/usr/bin/env python3
"""Test voice capture and transcription"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory.capture import VoiceCapture
from memory.processing import WhisperTranscriber
from memory.processing import LLMExtractor


def test_voice_pipeline():
    """Test voice capture → transcription → extraction"""
    
    print("🎤 Testing Voice Pipeline\n")
    
    # 1. Voice capture
    print("1️⃣  Testing voice capture...")
    voice = VoiceCapture()
    
    try:
        print("   Press Enter to start recording, then Enter again to stop.")
        input("   Ready? Press Enter to begin...")
        audio_path = voice.start_recording()
        print(f"   ✅ Audio saved: {audio_path}\n")
    except Exception as e:
        print(f"   ❌ Voice capture failed: {e}")
        return
    
    # 2. Transcription
    print("2️⃣  Testing transcription with Whisper...")
    transcriber = WhisperTranscriber()
    
    try:
        text = transcriber.transcribe(audio_path)
        print(f"   ✅ Transcribed text: '{text}'\n")
    except Exception as e:
        print(f"   ❌ Transcription failed: {e}")
        print("   Make sure Whisper is properly installed")
        return
    
    # 3. LLM Extraction
    print("3️⃣  Testing LLM extraction...")
    extractor = LLMExtractor()
    
    try:
        extracted = extractor.extract(text)
        print(f"   ✅ Extraction complete")
        print(f"   Thought type: {extracted.get('thought_type')}")
        print(f"   Summary: {extracted.get('summary')}")
        
        if extracted.get('actions'):
            print(f"   Actions found: {len(extracted['actions'])}")
            for action in extracted['actions']:
                print(f"     - {action['text']}")
        
        if extracted.get('people'):
            print(f"   People: {', '.join(extracted['people'])}")
        
        if extracted.get('topics'):
            print(f"   Topics: {', '.join(extracted['topics'])}")
        
    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        print("   Make sure Ollama is running with a model")
        return
    
    print("\n✅ Voice pipeline test complete!")
    print(f"   Audio: {audio_path}")
    print(f"   Text: {text}")
    print(f"   Type: {extracted.get('thought_type')}")


if __name__ == "__main__":
    test_voice_pipeline()