# Secure Pinterest Group PinBoard

A secure group messaging layer built on top of Pinterest. Members of a closed group can post encrypted messages as Pinterest pins. To any outside observer the pin description appears as random Base64 ciphertext. Only users with the group key can decrypt and read the actual content.

---

## How it works

This projectuses a hybrid encryption scheme; the same model used by TLS and PGP:

- **AES-256-GCM** encrypts each message. It is fast, handles any message length, and the GCM mode provides authentication. Any tampered ciphertexts are detected and rejected.
- **RSA-2048** never touches message content directly. It is only used to wrap (encrypt) the shared AES group key for each individual member, using their RSA public key. Only the holder of the matching private key can unwrap it.

Each user gets a self-signed X.509 certificate on registration that binds their username to their public key. The admin uses these certificates to manage group membership.

### Key management

| Action | What happens |
|---|---|
| Register | RSA-2048 key pair generated; self-signed X.509 cert issued; private key encrypted with user's password and stored |
| Add member | Admin wraps current AES group key with new member's RSA public key (from their cert) |
| Remove member | New AES group key generated; re-wrapped for every remaining member; removed user's entry deleted |
| Login | User's private key decrypted with their password; wrapped AES key unwrapped into session |

---

## Stack

- **Backend** — Python, Flask, SQLAlchemy, SQLite
- **Cryptography** — [`cryptography`](https://cryptography.io) (PyCA) for RSA, AES-GCM, and X.509
- **Frontend** — Jinja2 HTML templates, plain CSS
- **Pinterest** — Pinterest API v5 (OAuth2, pin create/read)

---

## Setup

```bash
pip install flask sqlalchemy cryptography bcrypt requests

export PINTEREST_APP_ID="your_app_id"
export PINTEREST_APP_SECRET="your_app_secret"
export PINTEREST_BOARD_ID="your_board_id"

python app.py
```

Visit `http://localhost:5000`. The first user to register automatically becomes the group admin.

---

## Project structure

```
├── crypto.py           # AES-256-GCM encrypt / decrypt
├── key_management.py   # RSA keys, X.509 certs, group key wrap / unwrap
├── database.py         # SQLite models — users, group keys, pins
├── pinterest_api.py    # Pinterest OAuth2 + pin post / fetch
├── app.py              # Flask routes
└── templates/          # HTML pages (login, register, board, admin)
```