import threading
import requests
import time
 
def ping_self():
    import os
    url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    while True:
        try:
            requests.get(f"{url}/", timeout=5)
        except:
            pass
        time.sleep(840)  # ping every 14 minutes
 
def start():
    t = threading.Thread(target=ping_self, daemon=True)
    t.start()
 