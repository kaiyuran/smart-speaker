
import asyncio
import websockets
import json
import base64
from faster_whisper import WhisperModel
import numpy as np

import soundfile as sf

HOST = "0.0.0.0"
PORT = 8765

#setup sst
model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


async def handler(ws):
    print("Client connected")
    audio_buffer = bytearray()

    async for message in ws:
        msg = json.loads(message)
        # print("Received message:", msg["type"])

        if msg["type"] == "audio":
            audio_buffer.extend(base64.b64decode(msg["data"]))

        elif msg["type"] == "end":
            print("End of utterance")

            inputAudio = np.frombuffer(audio_buffer, np.int16).astype(np.float32) / 32768.0
            print(inputAudio.shape)
            sf.write("output.wav", inputAudio, 16000) 

            # TODO 1: Speech-to-text
            print("Performing STT...")
            segments, info = model.transcribe(inputAudio, language="en")
            text = "".join([seg.text for seg in segments])
            print("STT:", text) 
            # text = "hello world"


            # =========================
            # TODO 2: Ollama
            reply = "Hello! I heard you."
            print("LLM:", reply)

            # =========================
            # TODO 3: Text-to-speech
            fake_pcm = b"\x00" * 16000  # placeholder audio

            await ws.send(json.dumps({
                "type": "audio",
                "data": base64.b64encode(fake_pcm).decode()
            }))

            await ws.send(json.dumps({"type": "done"}))

            audio_buffer.clear()

async def main():
    async with websockets.serve(handler, HOST, PORT):
        print(f"Server listening on {PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
