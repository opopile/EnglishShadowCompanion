import sys
import os

# Fix stdout/stderr for pythonw.exe (where sys.stdout is None)
class DummyStream:
    def write(self, x): pass
    def flush(self): pass

if sys.stdout is None:
    sys.stdout = DummyStream()
else:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = DummyStream()
else:
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import threading
import time

# Ensure current directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from translator import analyze_learning_card
from monitor import InputMonitor
from ui import LearningCardHUD

def main():
    hud = LearningCardHUD()
    last_processed = ""

    def on_sentence_detected(zh_text: str):
        nonlocal last_processed
        zh_text = zh_text.strip()
        if not zh_text or zh_text == last_processed or len(zh_text) < 2:
            return
        last_processed = zh_text
        
        # Analyze in background to keep UI buttery smooth
        def _worker():
            try:
                data = analyze_learning_card(zh_text)
                if data and data.get("english"):
                    hud.update_card(data)
            except Exception as e:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    monitor = InputMonitor(on_sentence_detected)
    monitor.start()

    try:
        hud.run()
    finally:
        monitor.stop()

if __name__ == "__main__":
    main()
