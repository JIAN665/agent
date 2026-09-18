import json
import os
import time

VOSK_AVAILABLE = False
try:
    from vosk import KaldiRecognizer, Model
    import queue
    import sounddevice as sd
    VOSK_AVAILABLE = True
except Exception:
    Model = None
    KaldiRecognizer = None
    queue = None
    sd = None
    VOSK_AVAILABLE = False


def recognize_from_microphone(model_dir, duration=20):
    if not VOSK_AVAILABLE or not os.path.exists(model_dir):
        raise RuntimeError(f"Vosk 不可用或模型目录不存在：{model_dir}")
    if queue is None or sd is None:
        raise RuntimeError("sounddevice 或 vosk 未安装")

    model = Model(model_dir)
    samplerate = 16000
    audio_queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            pass
        audio_queue.put(bytes(indata))

    final_text = ""
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16', channels=1, callback=callback):
        recognizer = KaldiRecognizer(model, samplerate)
        start = time.time()
        while time.time() - start < duration:
            try:
                data = audio_queue.get(timeout=1)
            except Exception:
                continue
            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()
                try:
                    final_text += json.loads(result).get('text', '') + ' '
                except Exception:
                    pass
        try:
            final = recognizer.FinalResult()
            final_text += json.loads(final).get('text', '') or ''
        except Exception:
            pass
    return final_text.strip()
