"""Phone camera over Wi-Fi: the server reads an MJPEG stream from a device on the local network and hands the page
its newest frame."""
import base64
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from mfnb.server import ipcam
from mfnb.server.app import create_app
from mfnb.storage.db import Store


def jpeg(k: int) -> bytes:
    return b"\xff\xd8frame%04d\xff\xd9" % k


class FakePhone(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass

    def _mjpeg(self, with_length: bool = True):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            for k in range(1, 400):
                f = jpeg(k)
                head = b"--frame\r\nContent-Type: image/jpeg\r\n"
                head += (b"Content-Length: %d\r\n" % len(f)) if with_length else b""
                self.wfile.write(head + b"\r\n" + f + b"\r\n")
                time.sleep(0.02)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path == "/video":
            return self._mjpeg()
        if self.path == "/nolength/video":
            return self._mjpeg(with_length=False)
        if self.path == "/shot.jpg":
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()
            self.wfile.write(jpeg(7))
            return
        if self.path == "/locked/video":
            ok = base64.b64encode(b"me:secret").decode()
            if self.headers.get("Authorization") != f"Basic {ok}":
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="cam"')
                self.end_headers()
                return
            return self._mjpeg()
        self.send_response(200 if self.path == "/" else 404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html>camera app</html>")


@pytest.fixture()
def client(tmp_path):
    yield TestClient(create_app(store=Store(tmp_path / "t.db"), assets_root=tmp_path / "assets"))
    ipcam.stop_all()


@pytest.fixture(scope="module")
def phone():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakePhone)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_split_frames():
    buf = bytearray(b"--x\r\nContent-Length: 6\r\n\r\n\xff\xd8ab\xff\xd9\r\n--x\r\n\r\n\xff\xd8cd\xff\xd9--x\r\n\r\n\xff\xd8e")
    assert ipcam.split_frames(buf) == [b"\xff\xd8ab\xff\xd9", b"\xff\xd8cd\xff\xd9"] and bytes(buf).endswith(b"\xff\xd8e")
    # a thumbnail inside a frame does not cut it when the part gives its length
    inner = b"\xff\xd8x\xff\xd8thumb\xff\xd9y\xff\xd9"
    buf = bytearray(b"Content-Length: %d\r\n\r\n" % len(inner) + inner)
    assert ipcam.split_frames(buf) == [inner]


def test_check_finds_the_stream_path(client, phone):
    r = client.get("/api/camera/check", params={"url": phone}).json()
    assert r["ok"] and r["url"].endswith("/video") and r["label"].startswith("Phone over Wi-Fi (127.0.0.1")


def test_newest_frame_only(client, phone):
    url = f"http://{phone}/video"
    first = client.get("/api/camera/frame", params={"url": url})
    assert first.status_code == 200 and first.headers["content-type"] == "image/jpeg"
    seq = int(first.headers["x-frame-seq"])
    time.sleep(0.3)                      # ~15 frames arrive meanwhile: only the newest is handed over
    nxt = client.get("/api/camera/frame", params={"url": url, "after": seq})
    assert int(nxt.headers["x-frame-seq"]) >= seq + 5 and nxt.content.startswith(b"\xff\xd8frame")
    assert ipcam.reader(url) is ipcam.reader(url)       # one connection to the phone, shared


def test_parts_without_length_and_snapshots(client, phone):
    r = client.get("/api/camera/frame", params={"url": f"http://{phone}/nolength/video"})
    assert r.status_code == 200 and r.content.startswith(b"\xff\xd8frame")
    r = client.get("/api/camera/frame", params={"url": f"http://{phone}/shot.jpg"})
    assert r.status_code == 200 and r.content == jpeg(7)


def test_not_a_stream(client, phone):
    r = client.get("/api/camera/check", params={"url": f"http://{phone}/"})
    # '/' is tried as /video first: that works; an explicit HTML page is refused
    assert r.status_code == 200
    r = client.get("/api/camera/check", params={"url": f"http://{phone}/page.html"})
    assert r.status_code == 502 and "404" in r.json()["detail"]


def test_login_in_the_address(client, phone):
    r = client.get("/api/camera/check", params={"url": f"http://{phone}/locked/video"})
    assert r.status_code == 502 and "login" in r.json()["detail"]
    r = client.get("/api/camera/check", params={"url": f"http://me:secret@{phone}/locked/video"}).json()
    assert r["ok"] and "secret" not in r["label"] and "me:secret@" in r["url"]   # kept to reconnect


@pytest.mark.parametrize("url,msg", [("http://8.8.8.8:8080/video", "own network"), ("ftp://192.168.1.2/video", "http"),
                                     ("", "Enter the address")])
def test_only_local_http_cameras(client, url, msg):
    r = client.get("/api/camera/check", params={"url": url})
    assert r.status_code == 400 and msg in r.json()["detail"]


def test_phone_not_answering(client):
    r = client.get("/api/camera/check", params={"url": "http://127.0.0.1:1/video"})
    assert r.status_code == 502 and "refused" in r.json()["detail"]


def test_discover_on_the_gateway(phone, monkeypatch):
    host, port = phone.split(":")
    monkeypatch.setattr(ipcam, "APP_PORTS", (int(port),))
    found = ipcam.discover([host, "8.8.8.8"])
    assert [f["url"] for f in found] == [f"http://{phone}/video"]
    assert isinstance(ipcam.default_gateways(), list)
