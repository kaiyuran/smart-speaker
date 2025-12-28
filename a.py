import speech_recognition as sr
with sr.Microphone(device_index=3) as source:
    sr.adjust_for_ambient_noise(source, duration=1)
    print("Say something!")
    audio = r.listen(source, timeout=5, phrase_time_limit=5)
