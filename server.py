
import asyncio
import websockets
import json
import base64
from faster_whisper import WhisperModel
import numpy as np
import time
import soundfile as sf
import ollama

HOST = "0.0.0.0"
PORT = 8765

#setup ollama
client = ollama.Client()
# url = "http://localhost:11434/api/chat"
ollama_model = "speakerAssistantv5"
history = []


#setup stt
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

            #Speech-to-text
            print("Performing STT...")
            # startTime = time.time()
            # segments, info = model.transcribe(inputAudio, language="en")
            # # print("STT took", time.time() - startTime, "seconds")
            # text = "".join([seg.text for seg in segments])
            # print("STT:", text) 
            
            text = "whats your name"  


            # =========================
            # TODO 2: Ollama
            # reply = "Hello! I heard you."
            history.append({"role": "user", "content": text})
            print("Sending to LLM...", history)
            response = ollama.chat(model=ollama_model,messages=history)
            history.append({"role": "assistant", "content": response.message.content})
            print("LLM:", response.message)





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
