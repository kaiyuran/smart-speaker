import asyncio
import sounddevice as sd
import pvporcupine
import websockets
import json
import base64
import time
import numpy as np
import pyaudio

# ===== CONFIG =====
ACCESSKEY = ""
KEYWORD = "picovoice"
WEBSOCKETURI = "ws://10.0.0.122:8765"

SAMPLERATE = 16000
CHANNELS = 1
baseRms = 8
rmsRolling = []

# ===== PORCUPINE =====
porcupine = pvporcupine.create(
    access_key=ACCESSKEY,
    keywords=[KEYWORD],
    sensitivities=[0.5]
)

#server responses

async def receiveResponses(ws, stream, ttsState):
    async for response in ws:
        try:
            msg = json.loads(response)
            if msg.get("type") == "audio" and ttsState["ttsActive"]:
                # Decode and play audio chunks
                audioData = base64.b64decode(msg["data"])
                stream.write(audioData)
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




async def runClient(baseRms):

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLERATE,
                    output=True)

    async with websockets.connect(WEBSOCKETURI) as ws:
        loop = asyncio.get_running_loop()

        wakeActive = False
        wakeStartTime = 0.0
        endSent = False
        ttsState = {"ttsActive": True} #tts state fopr interrrupts

        asyncio.create_task(receiveResponses(ws, stream, ttsState)) #start loop to listen for responses 

        def audioCallback(indata, frames, timeInfo, status):
            global rmsRolling
            nonlocal wakeActive, wakeStartTime, endSent

            if status:
                print(status)

            pcm = (indata[:, 0] * 32767).astype("int16")

            # Wake word
            if not wakeActive and porcupine.process(pcm) != -1: #not triggererd alr and detected
                wakeActive = True
                wakeStartTime = time.time()
                endSent = False
                #interrupt tts
                ttsState["ttsActive"] = False


                print("🔔 Wake word detected")
                
                rmsRolling = []

            if wakeActive:
                # Send audio
                pcm_b64 = base64.b64encode(pcm.tobytes()).decode("ascii")
                asyncio.run_coroutine_threadsafe(
                    ws.send(json.dumps({"type": "audio", "data": pcm_b64})),
                    loop
                )

                # check rolling 1 sec average rms averages after 2 sec passes
                
                rms = np.sqrt(np.mean(pcm.astype(np.float32) ** 2))
                rmsRolling.append(rms)
                if len(rmsRolling) > (2*(SAMPLERATE / porcupine.frame_length)):
                    rmsRolling.pop(0)



                if ((time.time() - wakeStartTime) >= 3.0) and np.mean(rmsRolling) <= baseRms:
                    endSent = True
                    wakeActive = False
                    asyncio.run_coroutine_threadsafe(
                        ws.send(json.dumps({"type": "end"})),
                        loop
                    )
                    ttsState["ttsActive"] = True
                    print("🛑 Sent END")


        with sd.InputStream(
            samplerate=SAMPLERATE,
            channels=CHANNELS,
            blocksize=porcupine.frame_length,
            callback=audioCallback
        ):
            print("🎤 Listening for wake word...")
            while True:
                await asyncio.sleep(0.1)

    stream.stop_stream()
    stream.close()
    p.terminate()

try:
    asyncio.run(runClient(baseRms))
finally:
    porcupine.delete()
