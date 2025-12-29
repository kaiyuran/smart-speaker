import asyncio
import websockets
import json
import numpy as np
import soundfile as sf
import base64
import pyaudio

# Replace with your server IP/port
WS_URI = "ws://10.0.0.122:8765"

# Audio chunk size in bytes
CHUNK_SIZE = 1024

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16

async def send_wav_chunks(file_path):
    # Initialize PyAudio for playback
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    output=True)
    
    async with websockets.connect(WS_URI) as ws:
        # Load WAV file
        data, sr = sf.read(file_path)  # float32 in [-1,1]
        
        # Convert to PCM16 bytes
        pcm_bytes = (data * 32768).astype(np.int16).tobytes()

        # Send audio in chunks
        for i in range(0, len(pcm_bytes), CHUNK_SIZE):
            chunk = pcm_bytes[i:i+CHUNK_SIZE]
            encoded = base64.b64encode(chunk).decode()

            message = {"type": "audio", "data": encoded}
            await ws.send(json.dumps(message))
            await asyncio.sleep(0.01)  # simulate streaming delay

        # Send end trigger
        await ws.send(json.dumps({"type": "end"}))
        print("Sent all audio chunks and end trigger")

        # Receive and play audio from server
        async for response in ws:
            try:
                msg = json.loads(response)
                if msg.get("type") == "audio":
                    # Decode and play audio from server
                    audio_data = base64.b64decode(msg["data"])
                    stream.write(audio_data)
                    print("Playing audio chunk from server")
                elif msg.get("type") == "end":
                    print("Server finished sending audio")
                    break
                elif msg.get("type") == "song":
                    print("Server sent song info:", msg.get("info", "No info"))
                else:
                    print("Server replied:", response)
            except json.JSONDecodeError:
                print("Server replied:", response)
    
    # Cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    asyncio.run(send_wav_chunks("zoo16.wav"))

# """