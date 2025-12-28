import soundfile as sf

data, samplerate = sf.read("output_resampled.wav")
print("Sample rate:", samplerate)
