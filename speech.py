import queue
import threading
import pythoncom
import win32com.client

class SpeechEngine:
    def __init__(self):
        self.queue = queue.Queue()
        self.enabled = True
        self.worker_thread = threading.Thread(target=self._run, daemon=True)
        self.worker_thread.start()

    def _run(self):
        # Initialize COM in this worker thread
        pythoncom.CoInitialize()
        voice = None
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            # Select an English voice if available
            voices = voice.GetVoices()
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription()
                if "english" in desc.lower() or "zira" in desc.lower() or "david" in desc.lower():
                    voice.Voice = voices.Item(i)
                    break
            voice.Rate = 0  # Normal conversational speed (-10 to 10)
            voice.Volume = 95
        except Exception as e:
            print(f"SAPI voice init failed: {e}")

        while True:
            text = self.queue.get()
            if not text:
                continue
            if voice and self.enabled:
                try:
                    # SVSFlagsAsync = 1
                    voice.Speak(text, 1)
                except Exception as e:
                    print(f"SAPI speak err: {e}")
            self.queue.task_done()

    def speak(self, text: str):
        if not text or not self.enabled:
            return
        # Discard previous speech to avoid backlog
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        self.queue.put(text)

# Singleton instance
engine = SpeechEngine()

def speak(text: str):
    engine.speak(text)

if __name__ == "__main__":
    speak("This is a robust speech engine test.")
    import time
    time.sleep(2)
