import sounddevice as sd
import numpy as np

print("🔊 Тест воспроизведения...")
print("Устройства вывода:")
for i, d in enumerate(sd.query_devices()):
    if d['max_output_channels'] > 0:
        print(f"  {i}: {d['name']}")

duration = 1.0
frequency = 440
samplerate = 44100

t = np.linspace(0, duration, int(samplerate * duration))
audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
audio_data = np.column_stack([audio_data, audio_data])  # стерео

print("▶ Воспроизведение...")
sd.play(audio_data, samplerate)
sd.wait()
print("✅ Готово!")