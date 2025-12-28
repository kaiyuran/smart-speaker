import librosa
import soundfile as sf

# Load original WAV
data, orig_sr = librosa.load("me_at_the_zoo.wav", sr=None)  # sr=None preserves original rate

# Resample to new rate (e.g., 16000 Hz)
target_sr = 16000
data_resampled = librosa.resample(data, orig_sr=orig_sr, target_sr=target_sr)

# Save new WAV
sf.write("output_resampled.wav", data_resampled, target_sr)
print(f"Saved resampled WAV at {target_sr} Hz")
