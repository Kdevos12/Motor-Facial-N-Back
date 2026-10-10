# Using your phone as the camera

A laptop webcam has to be about **2.8 m** away to see you from head to feet. A phone's main camera, held in
portrait, does it at about **1.7 m**, and the upper body fits at **1.2–1.5 m**. The phone sends its picture to
the computer, where the browser sees it as an ordinary webcam: everything stays on your computer.

If the camera still can't be far enough, use **Settings → Body & space → Framing → Upper body**: only arm and
trunk moves are used and the legs are not scored.

## Android: scrcpy (free, open source, USB, no watermark)

Needs Android 12 or newer. These commands are for Pop!_OS and Ubuntu.

**1. The virtual camera** (once):

```
sudo apt update
sudo apt install -y v4l2loopback-dkms v4l2loopback-utils v4l-utils
sudo modprobe v4l2loopback devices=1 video_nr=9 card_label="Phone (scrcpy)" exclusive_caps=1
```

To load it at every start-up:

```
echo v4l2loopback | sudo tee /etc/modules-load.d/v4l2loopback.conf
echo 'options v4l2loopback devices=1 video_nr=9 card_label="Phone (scrcpy)" exclusive_caps=1' | sudo tee /etc/modprobe.d/v4l2loopback.conf
```

- With **Secure Boot** on, the install asks for a password to enroll a key (MOK). Reboot, choose
  *Enroll MOK* on the blue screen and type that password; otherwise the module is refused.
- If `modprobe` fails after a kernel update: `sudo apt reinstall v4l2loopback-dkms`.

**2. scrcpy 5.0.1** (the Ubuntu package is too old for camera capture; this build includes `adb`):

```
cd ~/Downloads
wget https://github.com/Genymobile/scrcpy/releases/download/v5.0.1/scrcpy-linux-x86_64-v5.0.1.tar.gz
echo "9f969d30cc574816077edecda65719c1c70b0aee1df1ba5fa00779ac07b8fd6e  scrcpy-linux-x86_64-v5.0.1.tar.gz" | sha256sum -c
tar xf scrcpy-linux-x86_64-v5.0.1.tar.gz
cd scrcpy-linux-x86_64-v5.0.1
```

**3. On the phone:** Settings → About phone → tap *Build number* 7 times → Developer options → turn on
*USB debugging*. Plug the phone in and accept the prompt.

**4. Start the phone camera, before opening the app page:**

```
./scrcpy --video-source=camera --camera-facing=back --camera-size=1920x1080 --camera-fps=30 \
         --no-audio --v4l2-sink=/dev/video9 --no-video-playback
```

- `./scrcpy --list-cameras` and `./scrcpy --list-camera-sizes` show what the phone offers. A 4:3 size
  (for example `1440x1080`) or the ultra-wide camera (`--camera-id=…`) shows more of the room.
- Leave this terminal open while you train. If scrcpy stops, the app pauses the block: start it again, then
  click *Resume*.
- Without the cable (after a first USB connection): add `--tcpip`. It adds a little delay.

**5. In the app:** Settings → Cameras → *Moves (body)* → choose **Phone (scrcpy)**. If the phone stands in
portrait and the picture is sideways, choose *Rotate 90°* there (or add `--capture-orientation=90` to the
scrcpy command).

## iPhone (or Android): DroidCam

Install the DroidCam app on the phone and the DroidCam Linux client on the computer (droidcam.app). The free
version sends 640×480, which is enough for body tracking and for a face seen up close. It works over Wi-Fi, or
over USB (for an iPhone, also `sudo apt install usbmuxd`). Then choose the DroidCam camera in Settings →
Cameras.

Turn **off** any *mirror* option in DroidCam or Iriun. The app checks it anyway: the first time you use a camera
it asks you to raise your right hand (moves) or turn your head to your left (faces), and swaps left and right
back if the picture is mirrored.

## Browser

- **Chrome or Chromium** works best.
- **Firefox** (the Pop!_OS default) may not list the phone camera: open `about:config`, set
  `media.webrtc.camera.allow-pipewire` to `false`, restart Firefox. Firefox picks the camera in its permission
  prompt; if it remembered another one, click the camera icon in the address bar and reset the permission.
- A browser installed as a **Flatpak** needs access to devices (with Flatseal: *All devices*).

## Where to put the camera

- **Face the screen** during the whole block, not the camera. The camera may be off to one side: at the start
  of each motor block you stand still for 2 seconds facing the screen, the app measures where the camera sees
  you from and corrects for it. Best within 30°; above 45° the app warns, above 70° it asks you to move it.
- If it is to one side, put it **front-right** of you with an orthodox stance, **front-left** with a southpaw
  stance: the fighting stance then turns you toward it.
- Camera around chest-to-hip height, not tilted much.
- Whole body: about 1.7 m from a phone in portrait (2.8 m from a laptop webcam). Upper body: 1.2–1.5 m
  (1.5–2 m), with room above your raised hands.
- Training with your back to the camera is not supported: moves that would turn your back to it are left out,
  judged from where the camera actually is.
