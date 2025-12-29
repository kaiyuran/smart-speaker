
import asyncio
import websockets as ws
import json
import base64
from faster_whisper import WhisperModel
import numpy as np
import soundfile as sf
import ollama
from io import BytesIO 
from piper import PiperVoice
import wave

HOST = "0.0.0.0"
PORT = 8765

#setup ollama
client = ollama.Client()
# url = "http://localhost:11434/api/chat"
ollama_model = "speakerAssistantv7"
history = []

#setup stt
model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

#Set up punctuation list for making phrases
punctuation = [".", ",", "!", "?", ";", ":"]


#TTS
# Load voice
voice = PiperVoice.load("piper_models/en_US-ryan-low.onnx")


async def ttsStream(text): #phrase --> piper --> stream of pcm chunks -->
    # Placeholder TTS function
    def send():
        for chunk in voice.synthesize(text):
            asyncio.run_coroutine_threadsafe(
                ws.send(json.dumps({
                    "type": "audio",
                    "data": base64.b64encode(chunk.audio_int16_bytes).decode()
                })), asyncio.get_event_loop()
            )
    await asyncio.to_thread(send)

    # await asyncio.sleep(1)
    # return b"\x00" * 16000  # 1 second of silence as placeholder


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
            
            text = input("Enter simulated STT text: ")

            # =========================
            # TODO 2: Ollama
            # reply = "Hello! I heard you."
            history.append({"role": "user", "content": text})
            print("Sending to LLM...", history)
            # response = ollama.chat(model=ollama_model,messages=history)
            stream = ollama.chat(model=ollama_model,messages=history,stream=True)
            print("LLM:",end=" ")
            full_reply = ""
            # responseText = ""

            #songs
            songrec = False
            song = ""

            currphrase = ""

            for chunk in stream:
                # print(chunk)
                try:
                    token = chunk.message.content
                    full_reply += token
                    if "⚇" in full_reply and not "⚇" in token: #song recs
                        # print("["+token+"]")
                        # responseText = responseText.lower().rstrip().replace("recsong:","").rstrip()
                        songrec = True
                        song += token
                    elif not "⚇" in full_reply: #normal text
                        print(token, end="")
                        if any(p in token for p in punctuation): #check if its te end of a phrase
                            currphrase += token
                            await ttsStream(currphrase)
                            #TODO tts(currphrase) with streaming
                            currphrase = ""

                        responseText += token
                        currphrase += token

                except:
                    pass
            # print(full_reply)
            history.append({"role": "assistant", "content": full_reply})
            if songrec:
                song = song.lstrip()


            # print("Response to user:", responseText)
            print("Full song recommendation:", song)
            # print("LLM:", full_reply)


            # =========================
            # TODO 3: Text-to-speech
            # fake_pcm = b"\x00" * 16000  # placeholder audio



            # await ws.send(json.dumps({
            #     "type": "audio",
            #     "data": base64.b64encode(fake_pcm).decode()
            # }))

            await ws.send(json.dumps({"type": "done"}))

            audio_buffer.clear()

async def main():
    async with ws.serve(handler, HOST, PORT):
        print(f"Server listening on {PORT}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
