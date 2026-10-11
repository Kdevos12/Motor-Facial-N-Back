"""Browser test of the phone-over-Wi-Fi camera: a fake phone app serves a photo as an MJPEG stream (like IP Webcam),
the app connects to it from Settings, and MediaPipe must find the person through the relay in the camera check.

Usage: python tests/e2e/ipcam.py BASE_URL IMAGE OUT_DIR   (needs Playwright, Chromium and Pillow; a running server)
"""
import io
import json
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image
from playwright.sync_api import sync_playwright

BASE, IMAGE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CHROME = os.environ.get("CHROME_PATH", "/opt/pw-browsers/chromium")
PHOTO = Image.open(IMAGE).convert("RGB")


def frame(k: int) -> bytes:
    im = PHOTO.copy()
    im.putpixel((k % im.width, 0), (k * 37 % 255, 0, 0))     # a camera picture is never exactly the same
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return buf.getvalue()


class Phone(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if not self.path.startswith("/video"):
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=ipcam")
        self.end_headers()
        k = 0
        try:
            while True:
                jpg = frame(k)
                self.wfile.write(b"--ipcam\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpg) + jpg + b"\r\n")
                k += 1
                time.sleep(1 / 15)
        except (BrokenPipeError, ConnectionResetError):
            pass


def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    phone = ThreadingHTTPServer(("127.0.0.1", 0), Phone)
    threading.Thread(target=phone.serve_forever, daemon=True).start()
    addr = f"127.0.0.1:{phone.server_address[1]}"
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None,
                                    args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                          "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        # MediaPipe logs INFO lines as errors; the 502 is the deliberately wrong address below
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and not m.text.startswith("INFO:")
                and "502" not in m.text else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        prof = api("POST", "/api/profiles", {"name": "Phone tester"})
        page.goto(BASE + "/#/settings")
        page.wait_for_selector("text=Cameras")      # the app has stored its own choice of profile by now
        page.evaluate(f"localStorage.setItem('mfnb.profileId', '{prof['id']}')")
        page.reload()
        page.wait_for_selector("text=Cameras")
        # the user picks "Phone over Wi-Fi" for the moves and types the address the phone app shows
        moves = page.locator("select[aria-label='Camera']").first
        moves.select_option(value="__network")
        page.locator("input[placeholder^='e.g. 192.168']").first.fill(addr)
        page.locator("button:has-text('Connect')").first.click()
        page.wait_for_selector("text=Connected: Phone over Wi-Fi", timeout=15000)
        page.screenshot(path=f"{OUT}/ipcam_settings.png", full_page=True)
        cams = api("GET", f"/api/profiles/{prof['id']}")["settings"]["cameras"]["motor"]
        assert cams.get("url", "").endswith("/video"), cams
        # a wrong address explains what to do
        page.locator("input[placeholder^='e.g. 192.168']").first.fill("127.0.0.1:1")
        page.locator("button:has-text('Connect')").first.click()
        page.wait_for_selector("text=refused", timeout=15000)
        # camera check of a motor block, through the relay and MediaPipe
        page.goto(BASE + "/#/train/motor")
        page.wait_for_selector("text=Start block")
        page.click("text=Start block")
        page.wait_for_selector("text=Camera check", timeout=60000)
        page.wait_for_function("document.querySelector('.checklist li .dot')?.classList.contains('ok')", timeout=60000)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/ipcam_camcheck.png")
        browser.close()
    phone.shutdown()
    if errors:
        print("CONSOLE ERRORS:\n" + "\n".join(errors))
        return 1
    print("OK: phone stream relayed, person detected through it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
