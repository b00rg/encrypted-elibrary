# Secure Bookshelf

A secure social bookshelf application where users can create private group shelves, share book reviews, and manage group membership, all with end-to-end encryption. Users outside a shelf see reviews as raw ciphertext; only group members can decrypt them.

## Features

- **Encrypted reviews**: Book reviews are encrypted with AES-256-GCM; only shelf members can read them
- **Group shelf management**: Create shelves, invite members, or accept join requests
- **Secure member removal**: Removing a member triggers automatic re-keying. A fresh AES key is generated and distributed to all remaining members
- **Public-key certificate system**: Each user gets an RSA-2048 keypair and an X.509 certificate on registration
- **Admin global shelf**: The first registered user becomes admin and manages a global shared shelf

## Cryptographic Design

### Key Hierarchy

```
User password
    └── Decrypts RSA private key (PKCS8, password-based encryption)
            └── Unwraps AES-256 shelf key (RSA-OAEP / SHA-256)
                    └── Decrypts shelf content (AES-256-GCM)
```

### Algorithms

| Purpose | Algorithm |
|---|---|
| Content encryption | AES-256-GCM (12-byte nonce, authenticated) |
| Key wrapping | RSA-2048-OAEP (SHA-256) |
| User certificates | X.509 v3, self-signed, 365-day validity |
| Private key storage | PKCS8 + BestAvailableEncryption (password-derived) |
| Password hashing | bcrypt |

### Adding a Member

1. Owner holds the shelf AES key in their session
2. New member's X.509 certificate is fetched from the database
3. AES key is wrapped with the member's RSA public key (extracted from their cert)
4. Wrapped key stored in `ShelfMembership`; member unwraps it on next login using their private key

### Removing a Member

1. Member deleted from `ShelfMembership`
2. A **new** AES key is generated
3. New key is wrapped with each remaining member's public key and stored
4. `key_version` incremented. All future content uses the new key

## Setup

### Prerequisites

- Python 3.11+

### Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure

Create a `.env` file in the project root:

```
SECRET_KEY=your-secret-key-here
```

### Run

```bash
python run.py
```

The app runs at `http://localhost:5001`.

## Usage

1. **Register**: creates your RSA keypair, X.509 certificate, and (if you're the first user) the global shelf
2. **Login**: password decrypts your private key, which unwraps all your shelf AES keys into the session
3. **Create a shelf**: generates a new AES key for that shelf
4. **Invite a user**: their public key (from their cert) wraps a copy of the shelf key for them
5. **Write a review**: encrypted with the shelf AES key before being stored
6. **Non-members**: see the raw base64 ciphertext when viewing reviews

## Project Structure

```
app/
├── crypto.py            # AES-GCM encrypt/decrypt
├── key_management.py    # RSA keypair, X.509 certs, key wrap/unwrap
├── database.py          # SQLAlchemy models and queries
├── openlibrary.py       # OpenLibrary API integration
└── routes/
    ├── auth.py          # Register, login, logout
    ├── shelves.py       # Shelf CRUD
    ├── shelf_members.py # Add/remove members, re-keying
    ├── access_requests.py # Invitations and join requests
    ├── reviews.py       # Encrypted reviews
    └── shelf.py         # Global admin shelf
```

## Known Limitations

- **Self-signed certificates**: There is no root CA; certificates are self-signed. A production system would use a proper certificate authority.
- **Historical ciphertext**: Re-keying on member removal protects future content. Old ciphertext encrypted under the previous key remains in the database (re-encryption of historical data is not performed).
- **Session-held keys**: Decrypted AES keys live in the server-side Flask session for the duration of the login session.
