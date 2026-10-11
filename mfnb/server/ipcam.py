"""Relay an IP camera stream (a phone camera app over Wi-Fi) to the browser.

The browser cannot read pixels from another origin, so the local server reads the phone's MJPEG stream and hands
the page its newest frame (same origin). One reader per camera: the phone sees a single client (DroidCam accepts
only one), and stale frames are dropped instead of queued, so latency never builds up. Only addresses on the user's
own network are relayed (private ranges, link-local, Tailscale's 100.64.0.0/10 and this machine), so the app never
becomes a proxy to the internet.
"""
from __future__ import annotations

import base64
import ipaddress
import re
import socket
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

LOCAL_NETS = [ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16", "127.0.0.0/8",
    "fc00::/7", "fe80::/10", "::1/128")]
# Paths tried when only an address is given: IP Webcam and DroidCam (/video), older IP Webcam (/videofeed).
DEFAULT_PATHS = ("/video", "/videofeed")
# Ports of the common phone apps, for discovery on a phone hotspot: IP Webcam 8080, DroidCam 4747.
APP_PORTS = (8080, 4747)
CONNECT_TIMEOUT_S = 6.0
STREAM_TIMEOUT_S = 15.0
IDLE_STOP_S = 15.0         # a reader nobody polls for this long closes its connection
MAX_BUFFER = 8_000_000


class CameraURLError(ValueError):
    pass


def normalize(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise CameraURLError("Enter the address shown by the phone app, e.g. 10.0.0.5:8080")
    if "://" not in url:
        url = "http://" + url
    return url


def check_url(url: str) -> tuple[str, dict[str, str]]:
    """Validate a camera URL. Returns (url without credentials, request headers)."""
    p = urllib.parse.urlsplit(normalize(url))
    if p.scheme not in ("http", "https"):
        raise CameraURLError("The address must start with http:// or https://")
    if not p.hostname:
        raise CameraURLError("No address in the URL")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        raise CameraURLError(f"Unknown address: {p.hostname}") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not any(ip in net for net in LOCAL_NETS):
            raise CameraURLError("Only cameras on your own network can be used (a phone on the same Wi-Fi or "
                                 "hotspot, or a Tailscale address).")
    headers = {"User-Agent": "mfnb-ipcam"}
    if p.username:
        token = f"{urllib.parse.unquote(p.username)}:{urllib.parse.unquote(p.password or '')}"
        headers["Authorization"] = "Basic " + base64.b64encode(token.encode()).decode()
    host = p.hostname if ":" not in p.hostname else f"[{p.hostname}]"
    netloc = host + (f":{p.port}" if p.port else "")
    clean = urllib.parse.urlunsplit((p.scheme, netloc, p.path, p.query, ""))
    return clean, headers


def describe(err: BaseException) -> str:
    if isinstance(err, urllib.error.HTTPError):
        if err.code == 401:
            return "The phone app asks for a login: put it in the address, e.g. http://user:password@10.0.0.5:8080"
        return f"The phone app answered with error {err.code}: check the address (for IP Webcam it ends with /video)."
    reason = getattr(err, "reason", err)
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason):
        return ("The phone did not answer. Are the phone and this computer on the same network? Residence or "
                "campus Wi-Fi often blocks devices from seeing each other: connect this computer to the phone's "
                "hotspot instead (see the guide).")
    if isinstance(reason, ConnectionRefusedError) or "refused" in str(reason):
        return "The phone refused the connection: is the camera app started (IP Webcam: 'Start server')?"
    return f"Could not reach the phone: {reason}"


def _open(url: str, headers: dict[str, str], timeout: float):
    resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)
    ctype = resp.headers.get("Content-Type", "")
    return resp, ctype


def open_stream(url: str, timeout: float = CONNECT_TIMEOUT_S):
    """Open the camera stream. Returns (response, content type, url used). An address without a path tries the
    usual paths of the common phone apps. ``timeout`` applies to connecting and to each read. The url used keeps
    its login, if any (needed to reconnect)."""
    orig = normalize(url)
    p = urllib.parse.urlsplit(orig)
    candidates = [orig]
    if p.path in ("", "/"):
        candidates = [urllib.parse.urlunsplit((p.scheme, p.netloc, path, p.query, "")) for path in DEFAULT_PATHS]
    last: BaseException | None = None
    for cand in candidates:
        clean, headers = check_url(cand)
        try:
            resp, ctype = _open(clean, headers, timeout)
        except urllib.error.HTTPError as err:
            last = err
            if err.code == 404 and cand != candidates[-1]:
                continue
            raise
        if not ctype.lower().startswith(("multipart/", "image/")):
            resp.close()
            last = CameraURLError(f"This address is not a camera stream ({ctype or 'unknown type'}). For IP Webcam "
                                  "use the address it shows (port 8080), e.g. http://10.0.0.5:8080")
            continue
        return resp, ctype, cand
    assert last is not None
    raise last


def label(url: str) -> str:
    """Name shown for the camera (no credentials)."""
    p = urllib.parse.urlsplit(normalize(url))
    return f"Phone over Wi-Fi ({p.hostname}{':' + str(p.port) if p.port else ''})"


# ---- one reader per camera, keeping only the newest frame ---------------------------------------------------
_LEN = re.compile(rb"content-length:\s*(\d+)", re.I)


def split_frames(buf: bytearray) -> list[bytes]:
    """Remove the complete JPEG frames from an MJPEG byte buffer and return them (the rest stays in buf). Uses the
    part's Content-Length when present (robust to thumbnails inside a frame), else the JPEG start/end markers."""
    out = []
    while True:
        soi = buf.find(b"\xff\xd8")
        if soi < 0:
            del buf[:max(0, len(buf) - 1)]
            return out
        m = None
        for m in _LEN.finditer(bytes(buf[max(0, soi - 300):soi])):
            pass
        if m:
            n = int(m.group(1))
            if len(buf) < soi + n:
                return out
            out.append(bytes(buf[soi:soi + n]))
            del buf[:soi + n]
            continue
        eoi = buf.find(b"\xff\xd9", soi + 2)
        if eoi < 0:
            if len(buf) > MAX_BUFFER:
                buf.clear()
            return out
        out.append(bytes(buf[soi:eoi + 2]))
        del buf[:eoi + 2]


class Reader:
    """Reads one camera stream in a thread and keeps its newest JPEG frame."""

    def __init__(self, url: str):
        self.url = url
        self.frame: bytes | None = None
        self.seq = 0
        self.error: BaseException | None = None
        self.used = url
        self.started = time.monotonic()
        self.polled = time.monotonic()
        self.alive = True
        self.cond = threading.Condition()
        threading.Thread(target=self._run, daemon=True, name="ipcam-reader").start()

    def _run(self):
        try:
            resp, ctype, self.used = open_stream(self.url, timeout=STREAM_TIMEOUT_S)
        except BaseException as err:   # noqa: BLE001 - reported to the page
            self._fail(err)
            return
        buf = bytearray()
        try:
            if ctype.lower().startswith("image/"):     # a snapshot URL: poll it
                resp.close()
                self._poll_snapshots()
                return
            while self.alive and time.monotonic() - self.polled < IDLE_STOP_S:
                data = resp.read1(65536) if hasattr(resp, "read1") else resp.read(65536)
                if not data:
                    raise ConnectionError("The phone app stopped sending pictures.")
                buf += data
                for f in split_frames(buf)[-1:]:
                    self._publish(f)
        except BaseException as err:   # noqa: BLE001
            self._fail(err)
        finally:
            resp.close()
            self.alive = False

    def _poll_snapshots(self):
        clean, headers = check_url(self.used)
        while self.alive and time.monotonic() - self.polled < IDLE_STOP_S:
            with urllib.request.urlopen(urllib.request.Request(clean, headers=headers), timeout=STREAM_TIMEOUT_S) as r:
                self._publish(r.read())
            time.sleep(0.03)

    def _publish(self, frame: bytes):
        with self.cond:
            self.frame = frame
            self.seq += 1
            self.cond.notify_all()

    def _fail(self, err: BaseException):
        with self.cond:
            self.error = err
            self.alive = False
            self.cond.notify_all()

    def next_frame(self, after: int, wait_s: float) -> tuple[int, bytes | None]:
        """The newest frame if newer than ``after`` (waits up to wait_s for one), else (seq, None)."""
        self.polled = time.monotonic()
        with self.cond:
            self.cond.wait_for(lambda: self.seq > after or not self.alive, timeout=wait_s)
            if self.seq > after and self.frame is not None:
                return self.seq, self.frame
            return self.seq, None


_readers: dict[str, Reader] = {}
_lock = threading.Lock()


def reader(url: str) -> Reader:
    """The live reader of a camera URL, started on first use (validates the address first)."""
    check_url(url)
    key = normalize(url)
    with _lock:
        r = _readers.get(key)
        if r is None or not r.alive:
            r = _readers[key] = Reader(key)
        return r


def stop_all():
    with _lock:
        for r in _readers.values():
            r.alive = False
        _readers.clear()


# ---- finding the phone on its own hotspot ---------------------------------------------------------------------
def default_gateways() -> list[str]:
    """IPv4 gateways of this computer (Linux). On a phone's hotspot the gateway is the phone."""
    out: list[str] = []
    try:
        with open("/proc/net/route") as f:
            next(f)
            for line in f:
                cols = line.split()
                if len(cols) > 3 and int(cols[3], 16) & 0x2:    # RTF_GATEWAY
                    ip = socket.inet_ntoa(struct.pack("<L", int(cols[2], 16)))
                    if ip not in out:
                        out.append(ip)
    except (OSError, ValueError, StopIteration):
        pass
    return out


def discover(gateways: list[str] | None = None, timeout: float = 1.5) -> list[dict]:
    """Phone camera apps answering on a gateway (the phone, when this computer is on its hotspot)."""
    found = []
    for gw in (default_gateways() if gateways is None else gateways):
        try:
            ip = ipaddress.ip_address(gw)
        except ValueError:
            continue
        if not any(ip in net for net in LOCAL_NETS):
            continue
        for port in APP_PORTS:
            url = f"http://{gw}:{port}"
            try:
                resp, ctype, used = open_stream(url, timeout=timeout)
            except (OSError, ValueError):
                continue
            resp.close()
            found.append({"url": used, "label": label(used)})
    return found
