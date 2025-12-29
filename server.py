
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
import pyaudio

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
p = pyaudio.PyAudio()

def play_pcm(pcm_bytes, sample_rate=22050, channels=1):
    """Play raw PCM16 audio bytes via PyAudio (blocking)."""
    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    output=True)
    stream.write(pcm_bytes)
    stream.stop_stream()
    stream.close()


async def ttsStream(text, ws_conn): #phrase --> piper --> stream of pcm chunks -->
    print("generating TTS for:", text)

    def synthesize_chunks():
        chunks = []
        for audio_chunk in voice.synthesize(text):
            chunks.append(audio_chunk.audio_int16_bytes)
        return chunks

    # Synthesize in thread
    chunks = await asyncio.to_thread(synthesize_chunks)
    await asyncio.sleep(0.1)  # slight delay before sending

    # Send and play in async context
    for pcm_chunk in chunks:
        await ws_conn.send(json.dumps({
            "type": "audio",
            "data": base64.b64encode(pcm_chunk).decode()
        }))
        # print("playing chunk")
        # play_pcm(pcm_chunk, sample_rate=voice.config.sample_rate)


async def handler(ws):
    print("Client connected")
    audio_buffer = bytearray()

    async for message in ws:
        msg = json.loads(message)
        # print("Received message:", msg["type"])

        if msg["type"] == "audio":
            audio_buffer.extend(base64.b64decode(msg["data"]))

        elif msg["type"] == "end":
            print("End of talking")

            inputAudio = np.frombuffer(audio_buffer, np.int16).astype(np.float32) / 32768.0
            # print(inputAudio.shape)
            # sf.write("output.wav", inputAudio, 16000) 

            #Speech-to-text
            print("Performing STT...")
            # startTime = time.time()
            segments, info = model.transcribe(inputAudio, language="en")
            # print("STT took", time.time() - startTime, "seconds")
            text = "".join([seg.text for seg in segments])
            print("STT:", text) 
            
            # text = input("Enter simulated STT text: ")

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
                # try:
                token = chunk.message.content
                full_reply += token

                if "⚇" in token:#song rec trigger
                    pass

                elif "⚇" in full_reply: #song recs
                    # print("["+token+"]")
                    # responseText = responseText.lower().rstrip().replace("recsong:","").rstrip()
                    songrec = True
                    song += token
                else: #normal text
                    # responseText += token
                    currphrase += token

                    # print("current token is", token)
                    print(token, end="")
                    if any(p in token for p in punctuation): #check if its te end of a phrase
                        # print("end of phrase")
                        currphrase += token
                        print("current phrase is", currphrase)
                        await ttsStream(currphrase[:-1], ws)
                        #TODO tts(currphrase) with streaming
                        currphrase = ""



                # except:
                #     print("error in token stream")
                    # pass
            print(full_reply)
            history.append({"role": "assistant", "content": full_reply})
            if songrec:
                song = song.lstrip()
                # print("Response to user:", responseText)
                print("Full song recommendation:", song)
                await ws.send(json.dumps({
                    "type": "songrec",
                    "data": song
                }))
            
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
