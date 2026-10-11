"""Relay an IP camera stream (a phone camera app over Wi-Fi) to the browser.

The browser cannot read pixels from another origin, so the local server fetches the phone's MJPEG stream and
serves it from its own origin. Only addresses on the user's own network are relayed (private ranges, link-local,
Tailscale's 100.64.0.0/10 and this machine), so the app never becomes a proxy to the internet.
"""
from __future__ import annotations

import base64
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

LOCAL_NETS = [ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16", "127.0.0.0/8",
    "fc00::/7", "fe80::/10", "::1/128")]
# Paths tried when only an address is given: IP Webcam (/video), DroidCam (/video, /mjpegfeed).
DEFAULT_PATHS = ("/video", "/mjpegfeed")
CONNECT_TIMEOUT_S = 6.0
STREAM_TIMEOUT_S = 15.0


class CameraURLError(ValueError):
    pass


def normalize(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise CameraURLError("Enter the address shown by the phone app, e.g. http://192.168.43.1:8080/video")
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
            return "The phone app asks for a login: put it in the address, e.g. http://user:password@192.168.43.1:8080/video"
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
    usual paths of the common phone apps. ``timeout`` applies to connecting and to each read."""
    clean, headers = check_url(url)
    candidates = [clean]
    if urllib.parse.urlsplit(clean).path in ("", "/"):
        base = clean.rstrip("/")
        candidates = [base + p for p in DEFAULT_PATHS]
    last: BaseException | None = None
    for cand in candidates:
        try:
            resp, ctype = _open(cand, headers, timeout)
        except urllib.error.HTTPError as err:
            last = err
            if err.code == 404 and cand != candidates[-1]:
                continue
            raise
        if not ctype.lower().startswith(("multipart/", "image/")):
            resp.close()
            last = CameraURLError(f"This address is not a camera stream ({ctype or 'unknown type'}). For IP Webcam "
                                  "use http://PHONE-IP:8080/video")
            continue
        return resp, ctype, cand
    assert last is not None
    raise last


def iter_stream(resp, chunk: int = 64 * 1024):
    try:
        while True:
            data = resp.read1(chunk) if hasattr(resp, "read1") else resp.read(chunk)
            if not data:
                break
            yield data
    except OSError:
        return
    finally:
        resp.close()


def without_credentials(url: str) -> str:
    p = urllib.parse.urlsplit(normalize(url))
    if not p.username:
        return url
    return urllib.parse.urlunsplit((p.scheme, p.netloc.split("@", 1)[1], p.path, p.query, ""))


def label(url: str) -> str:
    """Name shown for the camera (no credentials)."""
    p = urllib.parse.urlsplit(normalize(url))
    return f"Phone over Wi-Fi ({p.hostname}{':' + str(p.port) if p.port else ''})"
