# Security

Twirra is a private, single-user tool. This repo is public, so no secrets ever live in it.

## Where secrets live

- **Server**: only in `server/.env` on the VPS, loaded via `python-dotenv`. `server/.env.example` has placeholders only. `.env` is git-ignored everywhere in this repo.
- **Mobile app**: JWT access/refresh tokens are written to `expo-secure-store`, which is backed by the OS keystore (Android Keystore / iOS Keychain). Tokens are never hardcoded, logged, or committed.

## Generating your own secrets

```bash
# JWT signing secret
openssl rand -hex 32

# App password hash (bcrypt)
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
```

Put both into `server/.env` (copied from `.env.example`), never into `.env.example` or any tracked file.

## Rotating secrets

Rotation only requires updating `server/.env` and restarting the service:

```bash
sudo systemctl restart twirra
```

Rotating `JWT_SECRET_KEY` invalidates all existing access/refresh tokens — the app will require a fresh login.

## Reporting an issue

This is a personal project without a bug bounty, but if you find a vulnerability, open a private security advisory on the GitHub repo rather than a public issue.
