"""Browser smoke test: runs the web app in demo (simulated) mode end to end.

Usage: python tests/e2e/smoke.py [base_url] [out_dir]
Needs Playwright + Chromium and a running server (`mfnb serve --no-browser`).
"""
import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
CHROME = os.environ.get("CHROME_PATH", "/opt/pw-browsers/chromium")


def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None,
                                    args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                          "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1366, "height": 860})
        # MediaPipe prints its own INFO lines through console.error
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and not m.text.startswith("INFO:") else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "/?simulate#/home")
        # first run: create a profile
        page.fill("input[placeholder='Your name']", "Tester")
        page.click("text=Create profile")
        page.wait_for_selector("text=Hi Tester")
        page.screenshot(path=f"{OUT}/01_home.png")
        pid = api("GET", "/api/profiles")[-1]["id"]
        # short blocks for the test
        api("PATCH", f"/api/profiles/{pid}", {"settings": {"motor": {"block_base": 4}, "facial": {"block_base": 4},
                                                         "iti_s": 0.5, "response_multiplier": 2.0,
                                                         "response_min_extra_s": 1.0}})
        page.goto(BASE + "/?simulate#/train/motor")
        page.wait_for_selector("text=Start block")
        page.screenshot(path=f"{OUT}/02_train.png")
        page.click("text=Start block")
        page.wait_for_selector("text=Camera check")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/03_camcheck.png")
        page.click("text=Start the block")
        page.wait_for_selector(".stage", timeout=15000)
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/04_watch.png")
        page.wait_for_selector(".phase:text-is('perform')", timeout=30000)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/05_perform.png")
        page.wait_for_selector("text=block report", timeout=120000)
        page.wait_for_timeout(800)
        page.screenshot(path=f"{OUT}/06_report.png", full_page=True)
        rows = page.locator("tr.clickable")
        if rows.count():
            rows.first.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=f"{OUT}/07_replay.png")
            page.keyboard.press("Escape")
        # facial block
        page.goto(BASE + "/?simulate#/train/facial")
        page.wait_for_selector("text=Start block")
        page.click("text=Start block")
        page.wait_for_selector("text=Camera check")
        page.wait_for_timeout(1200)
        page.click("text=Start the block")
        page.wait_for_selector(".stage", timeout=15000)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/08_face_watch.png")
        page.wait_for_selector("text=block report", timeout=120000)
        page.screenshot(path=f"{OUT}/09_face_report.png", full_page=True)
        # upper-body framing (camera too close / seated)
        api("PATCH", f"/api/profiles/{pid}", {"settings": {"motor": {"framing": "upper"}}})
        page.goto(BASE + "/?simulate#/train/motor")
        page.wait_for_selector("text=Start block")
        page.click("text=Start block")
        page.wait_for_selector("text=Room above your head")
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/09b_upper_camcheck.png")
        page.click("text=Start the block")
        page.wait_for_selector("text=block report", timeout=120000)
        upper = api("GET", f"/api/blocks/{api('GET', f'/api/dashboard/{pid}')['recent'][0]['block_id']}")
        assert upper["framing"] == "upper" and all(i["body_part"] == "upper" for i in upper["items"].values()), upper["framing"]
        api("PATCH", f"/api/profiles/{pid}", {"settings": {"motor": {"framing": "full"}}})
        # help page
        page.goto(BASE + "/?simulate#/help/camera")
        page.wait_for_selector("text=Using your phone as the camera")
        page.screenshot(path=f"{OUT}/09c_help.png", full_page=True)
        # library, dashboard, settings
        page.goto(BASE + "/?simulate#/library/motor")
        page.wait_for_selector(".lib-card")
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/10_library.png")
        page.locator(".lib-card").first.click()
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/11_library_item.png")
        page.keyboard.press("Escape")
        page.goto(BASE + "/?simulate#/library/facial")
        page.wait_for_selector(".lib-card")
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/12_library_face.png")
        page.goto(BASE + "/?simulate#/dashboard")
        page.wait_for_selector("text=Progress")
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/13_dashboard.png", full_page=True)
        page.goto(BASE + "/?simulate#/settings")
        page.wait_for_selector("text=Pacing & tolerance")
        page.wait_for_timeout(800)
        page.screenshot(path=f"{OUT}/14_settings.png", full_page=True)
        # calibration flows in demo mode
        page.goto(BASE + "/?simulate#/calibrate/body")
        page.wait_for_selector("text=Done!", timeout=60000)
        page.goto(BASE + "/?simulate#/calibrate/face")
        page.wait_for_selector("text=Done!", timeout=90000)
        prof = api("GET", f"/api/profiles/{pid}")
        assert "body" in prof["calibration"] and "face" in prof["calibration"], prof["calibration"]
        page.goto(BASE + "/?simulate#/library/motor")
        page.wait_for_selector(".lib-card")
        page.locator(".lib-card").nth(3).click()
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/16_library_item_calibrated.png")
        page.keyboard.press("Escape")
        # real tracker loads MediaPipe (fake camera feed: no person, but the model must load)
        page.goto(BASE + "/#/train/motor")
        page.wait_for_selector("text=Start block")
        page.click("text=Start block")
        page.wait_for_selector("text=Camera check", timeout=60000)
        page.wait_for_timeout(3000)
        page.click("summary:has-text('Camera')")
        page.wait_for_timeout(800)
        page.screenshot(path=f"{OUT}/15_real_camcheck.png")
        page.goto(BASE + "/#/train/facial")
        page.wait_for_selector("text=Start block")
        page.click("text=Start block")
        page.wait_for_selector("text=Camera check", timeout=60000)
        page.wait_for_timeout(3000)
        page.screenshot(path=f"{OUT}/17_real_face_camcheck.png")
        browser.close()
    dash = api("GET", f"/api/dashboard/{pid}")
    print("blocks:", dash["totals"]["blocks"], "motor history:", dash["modalities"]["motor"]["history"],
          "facial history:", dash["modalities"]["facial"]["history"])
    if errors:
        print("CONSOLE ERRORS:\n" + "\n".join(errors))
        return 1
    print("OK, no console errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
