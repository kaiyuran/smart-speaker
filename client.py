import asyncio
import sounddevice as sd
import pvporcupine
import websockets
import json
import base64
import time
import numpy as np
import pyaudio
import yt_dlp
import subprocess
import os
from dotenv import load_dotenv

# ===== CONFIG =====

load_dotenv("keys.env")  #load .env file
ACCESSKEY = os.getenv("picoApiKey")  #load from env
WEBSOCKETURI = "ws://10.0.0.122:8765"
KEYWORD = "picovoice"
keywordPath = "HeyJerryRPIPvporcupine.ppn"


SAMPLERATE = 16000
CHANNELS = 1
baseRms = 8
rmsRolling = []

# ===== PORCUPINE =====
porcupine = pvporcupine.create(
    access_key=ACCESSKEY,
    keyword_paths=[keywordPath], #for custom keyword
    #keywords=[KEYWORD], #for default keyword
    sensitivities=[0.5]
)

# youtube stream 

async def streamYouTube(query, stream, ttsState):
    options = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch'
    }

    def getUrl(): #retrieves song url from yt
        with yt_dlp.YoutubeDL(options) as ytdl: #use with to close after done
            metadata = ytdl.extract_info(query, download=False)
            url = metadata['entries'][0]['url']
            print("Streaming audio from URL:", url)
            return url

    url = await asyncio.to_thread(getUrl) #needs to be async

    process = subprocess.Popen(  #setup ffmpeg 
        [
            "ffmpeg",
            "-loglevel", "error",
            "-i", url,
            "-f", "s16le",
            "-ac", "1",
            "-ar", "16000",
            "-"
        ],
        stdout=subprocess.PIPE,
        bufsize=0
    )
    try: 
        while ttsState["ttsActive"]: 
            chunk = await asyncio.to_thread(process.stdout.read, 3200)  #read 100ms of audio
            if not chunk:
                break
            stream.write(chunk)
            await asyncio.sleep(0)  #allow other tasks to run


    finally:#close process when done or interrupt
        process.kill()
        process.stdout.close()


        



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
            elif msg.get("type") == "songrec":
                query = msg.get("data", "Unknown Song")
                print("Streaming song from YouTube:", query)
                asyncio.create_task(streamYouTube(query, stream, ttsState)) #stream the song

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
