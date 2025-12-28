import asyncio
import websockets
import json
import sounddevice as sd
import numpy as np
import base64

API_KEY = "YOUR_API_KEY"
MODEL = "gemini-2.5-live"

URI = (
    "wss://generativelanguage.googleapis.com/ws/"
    f"v1beta/models/{MODEL}:streamGenerateContent"
    f"?key={API_KEY}"
)

SAMPLE_RATE = 48000

def audio_callback(indata, frames, time, status):
    audio = (indata * 32767).astype(np.int16).tobytes()
    encoded = base64.b64encode(audio).decode()

    message = {
        "contents": [{
            "role": "user",
            "parts": [{
                "inline_data": {
                    "mime_type": "audio/pcm;rate=48000",
                    "data": encoded
                }
            }]
        }]
    }

    asyncio.run_coroutine_threadsafe(
        ws.send(json.dumps(message)),
        loop
    )

async def main():
    global ws, loop
    loop = asyncio.get_running_loop()

    async with websockets.connect(URI) as ws:
        print("🎤 Connected to Gemini Live")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
        ):
            async for msg in ws:
                data = json.loads(msg)
                if "candidates" in data:
                    for part in data["candidates"][0]["content"]["parts"]:
                        if "text" in part:
                            print("Gemini:", part["text"])

asyncio.run(main())
