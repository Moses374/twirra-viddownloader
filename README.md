# Twirra

A private Twitter/X video downloader: a FastAPI backend on your own VPS + a
minimal React Native (Expo) app that saves videos straight to your phone's
gallery.

Repo: https://github.com/Moses374/twirra-viddownloader

## Structure

```
twirra-viddownloader/
├── server/          # FastAPI + yt-dlp backend
│   ├── main.py
│   ├── auth.py
│   ├── downloader.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── app/             # React Native (Expo) mobile app
│   ├── App.js
│   ├── screens/HomeScreen.js
│   ├── services/api.js
│   ├── services/auth.js
│   └── package.json
├── SECURITY.md
└── README.md
```

---

## 1. VPS setup (Ubuntu)

Assumes a fresh Ubuntu 22.04+ VPS and a domain pointed at it (e.g. `twirra.yourdomain.com`).

### 1.1 System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip git ffmpeg
```

`ffmpeg` is required by yt-dlp for merging/remuxing some video formats.

### 1.2 Clone the repo

```bash
cd /opt
sudo git clone https://github.com/Moses374/twirra-viddownloader.git
sudo chown -R $USER:$USER twirra-viddownloader
cd twirra-viddownloader/server
```

### 1.3 Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1.4 Configure secrets

```bash
cp .env.example .env
openssl rand -hex 32   # copy the output into JWT_SECRET_KEY
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('CHOOSE-A-STRONG-PASSWORD'))"
# copy the output into APP_PASSWORD_HASH
nano .env   # fill in JWT_SECRET_KEY, APP_USERNAME, APP_PASSWORD_HASH, CORS_ORIGINS, etc.
```

Never commit `.env` — it's git-ignored by default.

### 1.5 Run with systemd

Create `/etc/systemd/system/twirra.service`:

```ini
[Unit]
Description=Twirra backend
After=network.target

[Service]
User=YOUR_LINUX_USER
WorkingDirectory=/opt/twirra-viddownloader/server
Environment="PATH=/opt/twirra-viddownloader/server/venv/bin"
ExecStart=/opt/twirra-viddownloader/server/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now twirra
sudo systemctl status twirra
```

### 1.6 Caddy reverse proxy (HTTPS)

Install Caddy:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

Edit `/etc/caddy/Caddyfile`:

```
twirra.yourdomain.com {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl restart caddy
```

Caddy automatically provisions and renews a Let's Encrypt TLS certificate for your domain.

### 1.7 Verify

```bash
curl https://twirra.yourdomain.com/health
# {"status":"ok"}
```

---

## 2. Expo APK build

### 2.1 Install tooling (on your dev machine)

```bash
cd app
npm install
npm install -g eas-cli
```

### 2.2 Point the app at your VPS

Edit `app/services/api.js` and set:

```js
export const API_BASE_URL = "https://twirra.yourdomain.com";
```

### 2.3 Log in to Expo / EAS

```bash
eas login
eas build:configure
```

This generates an `eas.json`. For a simple installable APK (not an AAB for the Play Store), make sure your Android build profile uses:

```json
{
  "build": {
    "preview": {
      "android": {
        "buildType": "apk"
      }
    }
  }
}
```

### 2.4 Build

```bash
eas build --platform android --profile preview
```

EAS builds in the cloud and gives you a download link for the `.apk` when done (also available at https://expo.dev under your project).

### 2.5 Install on your phone

Download the `.apk` link on your Android phone and open it (allow "install unknown apps" for your browser/file manager if prompted).

---

## 3. Pushing to GitHub safely

Before pushing, double check no secrets are staged:

```bash
git status
git diff --cached -- '*.env'   # should show nothing
```

Then:

```bash
git init   # if not already a repo
git remote add origin https://github.com/Moses374/twirra-viddownloader.git
git add .
git status   # review the file list — confirm no .env, no node_modules, no __pycache__
git commit -m "Initial commit: Twirra backend and mobile app"
git branch -M main
git push -u origin main
```

The `.gitignore` files at the repo root, in `server/`, and implicitly for `app/` already block `.env`, `__pycache__`, `node_modules`, and `.expo`. If `git status` ever shows one of those, stop and investigate before committing.

---

## API summary

| Method | Path            | Auth       | Description                              |
|--------|-----------------|------------|-------------------------------------------|
| POST   | `/auth/login`   | none       | Exchange username/password for tokens     |
| POST   | `/auth/refresh` | none       | Exchange refresh token for a new pair (rotates) |
| GET    | `/download`     | Bearer JWT | `?url=<tweet-url>` — streams the mp4, deletes it after serving |
| GET    | `/health`       | none       | Liveness check                            |

Access tokens expire in 15 minutes; refresh tokens in 90 days. The app refreshes silently on a 401 — you only log in once.
