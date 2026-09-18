import importlib.util

SR_AVAILABLE = False
try:
    import speech_recognition as sr
    if importlib.util.find_spec("pyaudio") is None:
        raise RuntimeError("PyAudio 未安装")
    SR_AVAILABLE = True
except Exception:
    sr = None
    SR_AVAILABLE = False


def recognize_from_microphone(language="zh-CN", timeout=5, phrase_time_limit=20):
    if not SR_AVAILABLE or sr is None:
        raise RuntimeError("speech_recognition / PyAudio 未安装，无法访问麦克风")
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    try:
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        return ""
    except Exception:
        return ""
