"""Phone camera over Wi-Fi: the server relays an MJPEG stream from a device on the local network."""
import base64
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from mfnb.server.app import create_app
from mfnb.storage.db import Store

FRAME = b"\xff\xd8fakejpeg\xff\xd9"


class FakePhone(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _mjpeg(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        for _ in range(3):
            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(FRAME))
            self.wfile.write(FRAME + b"\r\n")

    def do_GET(self):
        if self.path == "/video":
            return self._mjpeg()
        if self.path == "/locked/video":
            ok = base64.b64encode(b"me:secret").decode()
            if self.headers.get("Authorization") != f"Basic {ok}":
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="cam"')
                self.end_headers()
                return
            return self._mjpeg()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html>camera app</html>")


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(store=Store(tmp_path / "t.db"), assets_root=tmp_path / "assets"))


@pytest.fixture(scope="module")
def phone():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakePhone)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_check_finds_the_stream_path(client, phone):
    r = client.get("/api/camera/check", params={"url": phone}).json()
    assert r["ok"] and r["url"].endswith("/video") and r["content_type"].startswith("multipart/")
    assert r["label"].startswith("Phone over Wi-Fi (127.0.0.1")


def test_stream_is_relayed(client, phone):
    r = client.get("/api/camera/stream", params={"url": f"http://{phone}/video"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert r.content.count(FRAME) == 3


def test_not_a_stream(client, phone):
    r = client.get("/api/camera/check", params={"url": f"http://{phone}/index.html"})
    assert r.status_code == 400 and "not a camera stream" in r.json()["detail"]


def test_login_in_the_address(client, phone):
    r = client.get("/api/camera/check", params={"url": f"http://{phone}/locked/video"})
    assert r.status_code == 502 and "login" in r.json()["detail"]
    r = client.get("/api/camera/check", params={"url": f"http://me:secret@{phone}/locked/video"}).json()
    assert r["ok"] and "secret" not in r["label"]


@pytest.mark.parametrize("url,msg", [("http://8.8.8.8:8080/video", "own network"), ("ftp://192.168.1.2/video", "http"),
                                     ("", "Enter the address")])
def test_only_local_http_cameras(client, url, msg):
    r = client.get("/api/camera/check", params={"url": url})
    assert r.status_code == 400 and msg in r.json()["detail"]


def test_phone_not_answering(client):
    r = client.get("/api/camera/check", params={"url": "http://127.0.0.1:1/video"})
    assert r.status_code == 502 and "refused" in r.json()["detail"]
