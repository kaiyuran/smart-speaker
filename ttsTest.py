import pyaudio
from piper import PiperVoice

# Load voice
voice = PiperVoice.load("piper_models/en_US-ryan-low.onnx")

# Text to speak
text_to_speak = """Hello! This is a test of the Piper text-to-speech synthesis system."""

# PyAudio setup
p = pyaudio.PyAudio()

# We'll initialize stream later using first chunk's metadata
stream = None

# Stream audio
for chunk in voice.synthesize(text_to_speak):
    if stream is None:
        print(chunk)
        # Open PyAudio stream using first chunk's parameters
        stream = p.open(format=pyaudio.paInt16,
                        channels=chunk.sample_channels,
                        rate=chunk.sample_rate,
                        output=True)
    # Write raw PCM to speakers
    stream.write(chunk.audio_int16_bytes)

# Cleanup
if stream is not None:
    stream.stop_stream()
    stream.close()
p.terminate()
