# Using your phone as the camera

A laptop webcam has to be about **2.8 m** away to see you from head to feet. A phone's main camera, held in
portrait, does it at about **1.7 m**, and the upper body fits at **1.2–1.5 m**. The phone can stand across the
room and send its picture **over Wi-Fi**: no cable, no driver, nothing to install on the computer. The picture
goes from the phone to this computer only.

If the camera still can't be far enough, use **Settings → Body & space → Framing → Upper body**: only arm and
trunk moves are used and the legs are not scored.

## Over Wi-Fi (Android, no cable)

**1. The camera app.** Install **IP Webcam** from the Play Store (free with ads). Many apps look alike: the right
one's Play Store address ends in `id=com.pas.webcam`; its developer shows as Pavel Khlebovich or Thyoni Tech (his
company). Then:

- In *Video preferences*: back camera, video resolution **1280×720** (lower it if the picture lags), quality
  about **60**, orientation **portrait** if the phone stands upright.
- Android Settings → Apps → IP Webcam → Battery → **Unrestricted**, and keep the phone on a charger.
- Tap **Start server**. The address appears at the bottom of the screen, e.g. `http://10.20.30.40:8080`.

DroidCam also works (free version 640×480, address `http://PHONE-IP:4747`; close the DroidCam computer program
first, it accepts one viewer at a time).

**2. Connect in the app.** Settings → Cameras → *Moves (body)* → **Phone over Wi-Fi (camera app)…**, type the
address the phone shows, **Connect**. That's all if it says *Connected*.

**3. If it says the phone did not answer**: residence and campus Wi-Fi often stop devices from seeing each other.
Check that both are on the *same* Wi-Fi name first (residences often have several). If it still fails, use one of
these:

### a) The phone's own hotspot (most reliable)

1. Before switching, while you still have normal internet, run `mfnb fetch-assets` once: the app then works with
   no internet at all.
2. On the phone: Settings → Network & internet → Hotspot & tethering → **Wi-Fi hotspot** on (Samsung: Connections →
   Mobile Hotspot). Turn off *Turn off hotspot automatically* (otherwise it stops after 10 minutes without a
   device).
3. Connect the computer's Wi-Fi to the phone's hotspot. Start IP Webcam (*Start server*).
4. In the app: Settings → Cameras → *Phone over Wi-Fi* → **Find my phone (hotspot)**. On its own hotspot the phone
   is the computer's gateway; its address changes each time on recent Android, the button finds it for you.

The picture travels directly from the phone to the computer and **uses no mobile data**. But while the computer
is on the hotspot, its other internet traffic (updates, browser tabs) goes through the phone's mobile data: turn
**mobile data off** on the phone during the session, the camera keeps working. If your room has an Ethernet socket,
you can keep the internet on the cable and use the hotspot only for the camera:

```
nmcli connection modify "PHONE-HOTSPOT-NAME" ipv4.never-default yes ipv6.never-default yes
nmcli connection up "PHONE-HOTSPOT-NAME"
```

### b) A private tunnel: Tailscale (both stay on the residence Wi-Fi)

Install **Tailscale** on the phone (Play Store) and on the computer, and sign in with the same account on both:

```
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

The Tailscale app on the phone shows its address (`100.x.y.z`). In the app, connect to `100.x.y.z:8080`. When
the residence network blocks a direct path, Tailscale relays the picture through its servers: it still works but
can be slower; lower the resolution in IP Webcam (e.g. 640×480) if it lags. Keep the phone on Wi-Fi with mobile
data off, otherwise the tunnel may carry the video over mobile data. Some residences forbid VPN software: check
the rules.

### Good to know

- A delay of 0.1–0.3 s is normal and harmless: you get 2–3 times the move's duration to respond.
- If the picture freezes, the block pauses and tells you; fix the phone (screen, app, Wi-Fi), then *Resume*.
- If IP Webcam asks for a login, put it in the address: `http://user:password@10.20.30.40:8080`. It is stored
  only on this computer.
- Open-source alternative: *Android IP Camera* (F-Droid or its GitHub releases). Set a username and password in
  its settings, set TLS to *HTTP only*, and use `http://user:password@PHONE-IP:4444`. It blocks a computer for 15
  minutes after 5 failed logins, so type the login carefully.
- Use the phone for the moves and keep the laptop webcam for the face games: a face 2–3 m away is too small for
  reliable expressions.

## With a USB cable (Android): scrcpy

A cable gives the lowest delay (Android 12 or newer). It needs a virtual camera on the computer:

```
sudo apt update
sudo apt install -y v4l2loopback-dkms v4l2loopback-utils v4l-utils
sudo modprobe v4l2loopback devices=1 video_nr=9 card_label="Phone (scrcpy)" exclusive_caps=1
```

- Pop!_OS normally runs with Secure Boot off, so the module loads as is. If `modprobe` answers *Key was rejected
  by service*, Secure Boot is on (check with `mokutil --sb-state`): turn it off in the computer's firmware setup.
- If `modprobe` fails after a kernel update: `sudo apt reinstall v4l2loopback-dkms`.

scrcpy 5.0.1 (the Ubuntu package is too old for camera capture; this build includes `adb`):

```
cd ~/Downloads
wget https://github.com/Genymobile/scrcpy/releases/download/v5.0.1/scrcpy-linux-x86_64-v5.0.1.tar.gz
echo "9f969d30cc574816077edecda65719c1c70b0aee1df1ba5fa00779ac07b8fd6e  scrcpy-linux-x86_64-v5.0.1.tar.gz" | sha256sum -c
tar xf scrcpy-linux-x86_64-v5.0.1.tar.gz
cd scrcpy-linux-x86_64-v5.0.1
```

On the phone: Settings → About phone → tap *Build number* 7 times → Developer options → *USB debugging*. Plug it
in, accept the prompt, then start the camera **before** opening the app page:

```
./scrcpy --video-source=camera --camera-facing=back --camera-size=1920x1080 --camera-fps=30 \
         --no-audio --v4l2-sink=/dev/video9 --no-video-playback
```

- `./scrcpy --list-cameras` and `--list-camera-sizes` show what the phone offers; for the ultra-wide camera,
  replace `--camera-facing=back` with `--camera-id=<its id>` (the two cannot be combined).
- Phone upright: choose *Rotate 90°* in the app's camera settings (or add `--capture-orientation=90`).
- Leave the terminal open while you train. In the app, choose **Phone (scrcpy)** in Settings → Cameras.
- scrcpy without any cable: Android's *Wireless debugging* only turns on when the phone is connected to a Wi-Fi
  network, not while it hosts a hotspot. Use the Wi-Fi method above instead, or a short cable once
  (`./adb tcpip 5555`, unplug, then `./adb connect PHONE-IP:5555`). Use the `./adb` that comes with scrcpy, not
  the system one.

Browsers and virtual cameras: start scrcpy **before** opening the page (the virtual camera only appears while
something feeds it), then reload. If Firefox still does not list it, check in `about:config` that
`media.webrtc.camera.allow-pipewire` is `false`. A browser installed as a **Flatpak** needs access to devices (with
Flatseal: *All devices*). The Wi-Fi method above needs none of this.

## iPhone

The Wi-Fi method works with an iPhone camera app that serves an MJPEG address, or use **DroidCam** for iOS with
its Linux client over USB (`sudo apt install usbmuxd`), then choose the DroidCam camera in Settings → Cameras.

## Left and right

The first time you use a camera, the app asks you to raise your right hand (moves) or turn your head to your left
(faces). If the picture is mirrored, left and right are swapped back. Turning off any *mirror* option in the phone
app avoids it altogether.

## Where to put the camera

- **Face the screen** during the whole block, not the camera. The camera may be off to one side: at the start
  of each motor block you stand still for 2 seconds facing the screen, the app measures where the camera sees
  you from and corrects for it. Best within 30°; above 45° the app warns, above 70° it asks you to move it.
- If it is to one side, put it **front-right** of you with an orthodox stance, **front-left** with a southpaw
  stance: the fighting stance then turns you toward it.
- Camera around chest-to-hip height, not tilted much.
- Whole body: about 1.7 m from a phone in portrait (2.8 m from a laptop webcam). Upper body: 1.2–1.5 m
  (2–2.5 m), with room above your raised hands.
- Training with your back to the camera is not supported: moves that would turn your back to it are left out,
  judged from where the camera actually is.
