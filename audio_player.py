import os
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from pydub import AudioSegment
from typing import List, Tuple, Optional
from app_paths import get_resource_path

# Настройка пути к ffmpeg
ffmpeg_win = get_resource_path("ffmpeg.exe")
ffmpeg_linux = get_resource_path("ffmpeg")
ffmpeg_mac = get_resource_path("ffmpeg")

if os.path.exists(ffmpeg_win):
    AudioSegment.converter = ffmpeg_win
elif os.path.exists(ffmpeg_linux):
    AudioSegment.converter = ffmpeg_linux
elif os.path.exists(ffmpeg_mac):
    AudioSegment.converter = ffmpeg_mac


class SoundStream:
    def __init__(self, data: np.ndarray, sr: int, device: Optional[int], volume: float):
        # Гарантируем 2D массив (стерео)
        if len(data.shape) == 1:
            data = np.column_stack([data, data])
        
        self.data = data
        self.sr = sr
        self.device = device
        self.volume = volume
        self.pos = 0
        self.stopped = False
        self.channels = 2  # всегда стерео

        self.stream = sd.OutputStream(
            samplerate=sr,
            channels=self.channels,
            device=device,
            dtype="float32",
            callback=self._callback,
            finished_callback=self._finished,
        )
        self.stream.start()

    def _callback(self, outdata, frames, time, status):
        if self.stopped:
            outdata.fill(0)
            raise sd.CallbackStop()
        
        end = self.pos + frames
        chunk = self.data[self.pos:end]
        
        if len(chunk) < frames:
            # Копируем оставшееся
            outdata[:len(chunk)] = chunk * self.volume
            # Остальное заполняем нулями
            outdata[len(chunk):] = 0
            raise sd.CallbackStop()
        
        outdata[:] = chunk * self.volume
        self.pos = end

    def _finished(self):
        try:
            self.stream.close()
        except Exception:
            pass

    def stop(self):
        self.stopped = True
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass


class AudioPlayer:
    def __init__(self):
        self._lock = threading.Lock()
        self._active_streams: List[SoundStream] = []
        self._master_volume = 1.0
        self._primary_device: Optional[int] = None
        self._mirror_device: Optional[int] = None

    def get_output_devices(self) -> List[Tuple[int, str, int]]:
        try:
            devices = sd.query_devices()
        except Exception as e:
            print(f"Ошибка получения устройств: {e}")
            return []
        result = []
        for i, d in enumerate(devices):
            if d.get("max_output_channels", 0) > 0:
                result.append((i, d["name"], d["max_output_channels"]))
        return result

    def set_primary_device(self, device_id: Optional[int]) -> None:
        self._primary_device = device_id

    def set_mirror_device(self, device_id: Optional[int]) -> None:
        self._mirror_device = device_id

    def set_master_volume(self, volume: float) -> None:
        self._master_volume = max(0.0, min(1.0, volume))

    def _load_file(self, path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
        ext = os.path.splitext(path)[1].lower()
        try:
            print(f"🎵 Загрузка файла: {path}")
            
            if ext == ".mp3":
                audio = AudioSegment.from_file(path, format="mp3")
                sr = audio.frame_rate
                channels = audio.channels
                samples = np.array(audio.get_array_of_samples())
                max_val = float(2 ** (audio.sample_width * 8 - 1))
                data = samples.astype(np.float32) / max_val
                if channels == 2:
                    data = data.reshape((-1, 2))
                else:
                    # Конвертируем моно в стерео
                    data = np.column_stack([data, data])
                print(f"✅ MP3 загружен: {sr}Hz, {channels} каналов")
                return data, sr
            else:
                data, sr = sf.read(path, dtype="float32", always_2d=True)
                if data.shape[1] == 1:
                    # Конвертируем моно в стерео
                    data = np.column_stack([data, data])
                print(f"✅ Файл загружен: {sr}Hz, {data.shape[1]} каналов")
                return data, sr
        except Exception as e:
            print(f"❌ Ошибка загрузки {path}: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    def play(self, file_path: str, volume: float = 1.0) -> bool:
        data, sr = self._load_file(file_path)
        if data is None or sr is None:
            print(f"❌ Не удалось загрузить файл: {file_path}")
            return False

        final_volume = volume * self._master_volume
        print(f"▶ Воспроизведение: {file_path} (громкость: {final_volume:.2f})")

        with self._lock:
            try:
                if self._primary_device is not None or self._mirror_device is None:
                    stream = SoundStream(data, sr, self._primary_device, final_volume)
                    self._active_streams.append(stream)

                if self._mirror_device is not None:
                    stream = SoundStream(data, sr, self._mirror_device, final_volume)
                    self._active_streams.append(stream)

                self._cleanup_finished()
                return True
            except Exception as e:
                print(f"❌ Ошибка воспроизведения: {e}")
                import traceback
                traceback.print_exc()
                return False

    def stop_all(self) -> None:
        with self._lock:
            for s in self._active_streams:
                try:
                    s.stop()
                except Exception:
                    pass
            self._active_streams.clear()
        print(" Все звуки остановлены")

    def _cleanup_finished(self) -> None:
        self._active_streams = [s for s in self._active_streams if s.stream.active]

    def is_playing(self) -> bool:
        with self._lock:
            self._cleanup_finished()
            return len(self._active_streams) > 0

    def quit(self) -> None:
        self.stop_all()