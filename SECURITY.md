# Security

Twirra is a private, single-user tool. This repo is public, so no secrets ever live in it.

## Where secrets live

- **Server**: only in `server/.env` on the VPS, loaded via `python-dotenv`. `server/.env.example` has placeholders only. `.env` is git-ignored everywhere in this repo.
- **Mobile app runtime**: JWT access/refresh tokens are written to `expo-secure-store`, which is backed by the OS keystore (Android Keystore / iOS Keychain). Tokens are never hardcoded, logged, or committed.
- **Android release signing**: the app's release keystore (`twirra-release.keystore`) lives only at `~/.android-keystores/` on the machine that generated it — never in this repo. `*.keystore` and `*.jks` are git-ignored everywhere. For CI builds, the keystore (base64-encoded) and its passwords are stored as **GitHub Actions repo secrets** (`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_PASSWORD`, `KEY_ALIAS`) and injected only as environment variables during the `Build release APK` step in `.github/workflows/build-apk.yml` — never written to a tracked file or printed to logs.

### Keystore backup — this one matters

Unlike server secrets, **the release keystore cannot be regenerated if lost.** If it's gone, any future APK build will be signed with a different key, and Android refuses to install an update over an existing install signed by a different key — you'd have to uninstall Twirra and lose local app data (SecureStore tokens, cached files) before reinstalling.

Keep a backup of `~/.android-keystores/twirra-release.keystore` somewhere durable (encrypted cloud storage, password manager attachment, etc.) outside of this machine alone.

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

Rotating the **GitHub Actions signing secrets** (e.g. after generating a new keystore) is done via:

```bash
gh secret set KEYSTORE_BASE64 --repo Moses374/twirra-viddownloader < keystore.b64
gh secret set KEYSTORE_PASSWORD --repo Moses374/twirra-viddownloader --body "<new password>"
gh secret set KEY_PASSWORD --repo Moses374/twirra-viddownloader --body "<new password>"
gh secret set KEY_ALIAS --repo Moses374/twirra-viddownloader --body "<new alias>"
```

Note: rotating to a genuinely new keystore (not just new passwords on the same one) means future builds can no longer update existing installs — see the keystore backup note above.

## Reporting an issue

This is a personal project without a bug bounty, but if you find a vulnerability, open a private security advisory on the GitHub repo rather than a public issue.
