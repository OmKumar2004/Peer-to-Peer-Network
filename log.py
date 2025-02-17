import threading
import time

lock = threading.Lock()
LOG_FILE = "OUTPUT.txt"

def log(message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} - {message}\n"
    with lock:
        with open(LOG_FILE, "a") as f:
            f.write(entry)
