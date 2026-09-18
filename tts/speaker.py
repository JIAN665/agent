import os
import subprocess


def speak_text(text):
    text = str(text or "").strip()
    if not text:
        return

    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text)
        return
    except Exception:
        pass

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return
    except Exception:
        pass

    if os.name == "nt":
        try:
            safe_text = text.replace('"', '\\"')
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    f"$s = New-Object -ComObject SAPI.SpVoice; $s.Speak(\"{safe_text}\")",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return
        except Exception:
            pass
