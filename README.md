<h1 align="center">DumbConvert</h1>

<p align="center">
  Film negatives in, pictures out.<br>
  A quick converter for camera scans, before you catalogue them in your favourite program.
</p>

<p align="center">
  <a href="https://github.com/jiijii0/dumbconvert/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/jiijii0/dumbconvert?label=release&color=2ee6ff"></a>
  <img alt="Status: beta" src="https://img.shields.io/badge/status-beta-orange">
  <img alt="macOS, Apple Silicon" src="https://img.shields.io/badge/macOS-Apple%20Silicon-000000?logo=apple&logoColor=white">
  <img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776AB?logo=python&logoColor=white">
  <a href="https://github.com/marcinz606/NegPy"><img alt="Engine: NegPy" src="https://img.shields.io/badge/engine-NegPy-8a2be2"></a>
  <a href="LICENSE"><img alt="Licence: GPLv3" src="https://img.shields.io/badge/licence-GPLv3-blue"></a>
</p>

<p align="center">
  <a href="https://github.com/jiijii0/dumbconvert/releases/tag/v0.1.0-beta.2"><b>macOS beta</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/jiijii0/dumbconvert/releases/tag/windows-linux-alpha.1"><b>Windows alpha</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/jiijii0/dumbconvert/releases/tag/windows-linux-alpha.1"><b>Linux alpha</b></a>
  <br>
  <sub>The Windows and Linux alphas have not been tested yet.</sub>
</p>

![DumbConvert](docs/screenshot.png)

## Why it's nice

- **Drop and go.** Drop a roll, get good colour straight away.
- **Decluttered.** Six faders, like a lab scanner. The rest stays folded away.
- **No library.** No projects, no catalogue, no sidecar files. Open, convert, close.
- **Rolls match.** A roll is measured as one, so its frames share the same colour.
- **Keyboard first.** Everything has a key, and every key can be changed.
- **Film data in the file.** Stock, camera, lens, date and place go into the EXIF.
- **Any format.** JPEG, HEIC, TIFF, PNG, AVIF, JPEG XL, WebP, or DNG for your raw editor.
- **Dust, your way.** Click a speck, or draw around an area and let it find the dust and scratches.
- **Contact sheets.** A whole roll on one sheet, film edges included.
- **Private.** Your scans are never changed and never uploaded.

Made for negatives scanned with a digital camera over a white light, colour or B&W.

## iPad and other tablets (self-hosted)

DumbConvert also runs as a small web server, so you can use it from Safari on an iPad. The conversion
happens on the machine that runs the server; your scans never go anywhere else.

```sh
pip install -r requirements.txt -r requirements-web.txt   # plus the NegPy steps in CONTRIBUTING.md
DUMBCONVERT_TOKEN=pick-a-password python -m simpleneg.web --host 0.0.0.0 --port 8000
```

Open `http://<that machine>:8000/?token=pick-a-password` on the iPad (use Share > Add to Home Screen
for a full-screen app). Add scans from the Files app, drag the faders, then Export: the result goes
to the share sheet, so you can save it to Photos or Files. Use it on your home network or behind a VPN
such as Tailscale; do not expose it to the internet. This version has the six faders, rotate/mirror,
B&W, film stock and roll matching; the dust, crop and contact-sheet tools are desktop-only for now.

### In Docker (NAS or home server)

Every push to `main` builds an image (amd64 and arm64) and publishes it to
`ghcr.io/jedwardrico/dumbconvert:latest`. On the NAS, use `docker-compose.yml`: set the password and run
`docker compose up -d`. To update, `docker compose pull && docker compose up -d`, or let Watchtower do it.
If the package is private, `docker login ghcr.io` with a token that has `read:packages` first.
To build it yourself instead: `git clone --recurse-submodules`, then `docker build -t dumbconvert .`.

## Install

1. Download the zip from the [macOS beta](https://github.com/jiijii0/dumbconvert/releases/tag/v0.1.0-beta.2) and unzip it.
2. Move **DumbConvert** to Applications.

Windows and Linux (Flatpak): see the [alpha release](https://github.com/jiijii0/dumbconvert/releases/tag/windows-linux-alpha.1)
for the files and how to install them. These builds have not been tested yet.

### First launch

The beta is not signed by Apple, so macOS blocks it once.

1. Open DumbConvert. macOS says it cannot be opened. Click **Done**.
2. Go to **System Settings › Privacy & Security**, scroll down, click **Open Anyway**.
3. Click **Open Anyway** again and confirm.

On macOS 14 or older: right-click the app, choose **Open**, then **Open**.

Still blocked? Run this once in Terminal:

```sh
xattr -dr com.apple.quarantine /Applications/DumbConvert.app
```

## Run from source

Needs Python 3.13+ and Rust (`brew install rust`).

```sh
git clone --recurse-submodules https://github.com/jiijii0/dumbconvert.git
cd dumbconvert
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install ./vendor/negpy/negpy_core
.venv/bin/pip install --no-deps -e ./vendor/negpy
./run.command
```

`./packaging/build.sh` builds the app and its zip into `dist/`.

Want to help? See [CONTRIBUTING.md](CONTRIBUTING.md): how to run the tests, and what makes a pull
request easy to merge.

## More

Every key, how it works and why the defaults are what they are: [docs/details.md](docs/details.md).

The place search sends the text you type to [Photon](https://photon.komoot.io), a free
OpenStreetMap search. Nothing else leaves your Mac.

## Thanks

To [NegPy](https://github.com/marcinz606/NegPy), by marcinz606 and its contributors. The conversion
engine is theirs; I built on it and tuned it for this app.

GPLv3, like NegPy. See [LICENSE](LICENSE).

## Support

If DumbConvert saves you some time, you can buy me a coffee.

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jiijii0)
