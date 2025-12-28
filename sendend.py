"""
import asyncio
import websockets
import json

# Replace with your server IP/port
WS_URL = "ws://172.20.0.1:8765"

async def send_end_trigger():
    async with websockets.connect(WS_URL) as ws:
        # Send the "end" message
        msg = {"type": "end"}
        await ws.send(json.dumps(msg))
        print("Sent end trigger")

        # Optional: wait for server response
        response = await ws.recv()
        print("Server replied:", response)

if __name__ == "__main__":
    asyncio.run(send_end_trigger())

"""

import asyncio
import websockets
import json
import numpy as np
import soundfile as sf
import base64

# Replace with your server IP/port
WS_URI = "ws://172.20.0.1:8765"

# Audio chunk size in bytes
CHUNK_SIZE = 1024

async def send_wav_chunks(file_path):
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

        # Optional: wait for server response
        async for response in ws:
            print("Server replied:", response)

if __name__ == "__main__":
    asyncio.run(send_wav_chunks("example16.wav"))

# """