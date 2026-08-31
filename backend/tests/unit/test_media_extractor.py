import pytest
import os
import tempfile
import wave

from app.services.extractors.audio_video import AudioVideoExtractor

def test_wav_audio_metadata():
    extractor = AudioVideoExtractor()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        temp_path = f.name
        
    try:
        # Create a valid 2-second WAV file with 44.1kHz stereo silence
        with wave.open(temp_path, "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            # 2 seconds = 44100 frames * 2 channels * 2 bytes/sample * 2 seconds
            wav.writeframes(b"\x00" * 44100 * 2 * 2 * 2)
            
        res = extractor.extract(temp_path)
        
        assert res.metadata["format"] == "WAV"
        assert res.metadata["channels"] == 2
        assert res.metadata["sample_rate"] == 44100
        assert res.metadata["duration"] == 2.0
        assert res.metadata["codec"] == "PCM"
        assert res.text == ""
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_mp4_video_metadata_fallback():
    extractor = AudioVideoExtractor()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(b"mock video container")
        temp_path = f.name
        
    try:
        res = extractor.extract(temp_path)
        assert res.metadata["format"] == "MP4"
        assert "not supported" in res.metadata["metadata_warning"]
        assert res.text == ""
    finally:
        os.remove(temp_path)
