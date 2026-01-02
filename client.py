import asyncio
import sounddevice as sd
import pvporcupine
import websockets
import json
import base64
import time
import numpy as np

# ===== CONFIG =====
ACCESS_KEY = ""
KEYWORD = "picovoice"
WEBSOCKET_URI = "ws://10.0.0.122:8765"

SAMPLE_RATE = 16000
CHANNELS = 1
# RECORD_SECONDS = 5
baseRms = 8
rmsRollling = []

# ===== PORCUPINE =====
porcupine = pvporcupine.create(
    access_key=ACCESS_KEY,
    keywords=[KEYWORD],
    sensitivities=[0.5]
)

async def run_client(baseRms):
    async with websockets.connect(WEBSOCKET_URI) as ws:
        loop = asyncio.get_running_loop()

        wake_active = False
        wake_start_time = 0.0
        end_sent = False


        def audio_callback(indata, frames, time_info, status):
            global rmsRolling
            nonlocal wake_active, wake_start_time, end_sent

            if status:
                print(status)

            pcm = (indata[:, 0] * 32767).astype("int16")

            # Wake word
            if not wake_active and porcupine.process(pcm) != -1: #not triggererd alr and detected
                wake_active = True
                wake_start_time = time.time()
                end_sent = False
                print("🔔 Wake word detected")
                rmsRolling = []

            if wake_active:
                # Send audio
                pcm_b64 = base64.b64encode(pcm.tobytes()).decode("ascii")
                asyncio.run_coroutine_threadsafe(
                    ws.send(json.dumps({"type": "audio", "data": pcm_b64})),
                    loop
                )

                # check rolling 1 sec average rms averages after 2 sec passes
                
                rms = np.sqrt(np.mean(pcm.astype(np.float32) ** 2))
                rmsRolling.append(rms)
                if len(rmsRolling) > (2*(SAMPLE_RATE / porcupine.frame_length)):
                    rmsRolling.pop(0)



                if ((time.time() - wake_start_time) >= 3.0) and np.mean(rmsRolling) <= baseRms:
                # if not end_sent and time.monotonic() - wake_start_time >= RECORD_SECONDS:
                    end_sent = True
                    wake_active = False
                    asyncio.run_coroutine_threadsafe(
                        ws.send(json.dumps({"type": "end"})),
                        loop
                    )
                    print("🛑 Sent END")

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


        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=porcupine.frame_length,
            callback=audio_callback
        ):
            print("🎤 Listening for wake word...")
            while True:
                await asyncio.sleep(0.1)

try:
    asyncio.run(run_client(baseRms))
finally:
    porcupine.delete()
