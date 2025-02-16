import time
import fcntl

def log_message(msg):
    try:
        with open("OUTPUT.txt", "a") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX)
            except Exception as e:
                print("Warning: file locking not available", e)
            f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
            f.flush()
            try:
                fcntl.flock(f, fcntl.LOCK_UN)
            except Exception as e:
                print("Warning: unlocking error", e)
    except Exception as e:
        print("Logging error:", e)
