// Webcam access (one shared stream).
let stream = null;

export async function startCamera(deviceId) {
  if (stream) return stream;
  if (!navigator.mediaDevices?.getUserMedia) throw new Error('This browser cannot access a camera.');
  stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 }, ...(deviceId ? { deviceId: { exact: deviceId } } : { facingMode: 'user' }) },
  });
  return stream;
}

export function stopCamera() {
  if (stream) stream.getTracks().forEach((t) => t.stop());
  stream = null;
}

export async function attachVideo(video) {
  const s = await startCamera();
  video.srcObject = s;
  video.muted = true;
  video.playsInline = true;
  await video.play();
  if (video.readyState < 2) await new Promise((r) => video.addEventListener('loadeddata', r, { once: true }));
  return video;
}

export async function listCameras() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((d) => d.kind === 'videoinput');
}
