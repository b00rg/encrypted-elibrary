"""
app.py - Flask application entry point and route definitions

This module wires together all other modules into a working web application.

Routes:
  GET  /                  Home page — redirects to /board if logged in
  GET  /register          Registration form
  POST /register          Create account, generate keys and certificate
  GET  /login             Login form
  POST /login             Verify password, load wrapped group key
  GET  /logout            Clear session
  GET  /board             View all pins (decrypted for members, ciphertext for others)
  POST /post              Encrypt and post a new pin to Pinterest
  GET  /connect           Redirect to Pinterest OAuth2
  GET  /callback          Handle Pinterest OAuth2 callback
  GET  /admin             Admin panel — view members (admin only)
  POST /admin/add         Add a member to the secure group (admin only)
  POST /admin/remove      Remove a member and re-key the group (admin only)

Session keys:
  username        Logged-in username
  is_admin        Whether the user is the group admin
  aes_key_hex     Hex-encoded AES group key (in-memory only, never stored plaintext)
  pinterest_token Pinterest OAuth2 access token
"""

import binascii

import bcrypt
from flask import (Flask, flash, redirect, render_template,
                   request, session, url_for)

from crypto import decrypt_message, encrypt_message, is_encrypted
from database import (create_user, delete_user, get_all_member_certificates,
                      get_all_pins, get_all_users, get_user, get_wrapped_key,
                      init_db, pin_exists, save_pin, save_wrapped_key)
from key_management import (add_member, deserialize_private_key,
                             generate_certificate, generate_rsa_keypair,
                             get_username_from_cert, remove_member,
                             serialize_certificate, serialize_private_key,
                             unwrap_group_key, wrap_group_key,
                             deserialize_certificate, deserialize_public_key,
                             serialize_public_key)
from pinterest_api import (exchange_code_for_token, fetch_board_pins,
                            get_authorisation_url, get_pinterest_user,
                            post_encrypted_pin)

app = Flask(__name__)

# Secret key for signing Flask session cookies.
# In production, load this from an environment variable — never hardcode it.
app.secret_key = "CHANGE_ME_IN_PRODUCTION"


# ---------------------------------------------------------------------------
# Initialise database on startup
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def get_aes_key_from_session() -> bytes | None:
    """
    Retrieve the AES group key from the current session.

    The key is stored as a hex string in the session cookie (which is
    signed but not encrypted). In a higher-security system you would
    store only a reference and keep the key server-side in a cache
    like Redis. For this prototype, the signed cookie is acceptable.

    Returns:
        bytes: 32-byte AES key, or None if not in session
    """
    hex_key = session.get("aes_key_hex")
    if hex_key:
        return binascii.unhexlify(hex_key)
    return None


def login_required(f):
    """
    Decorator: redirect to /login if the user is not authenticated.
    Usage: @login_required above a route function.
    """
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """
    Decorator: return 403 if the logged-in user is not the group admin.
    """
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("board"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

@app.route("/")
def index(): 
    """Redirect logged-in users to the board, others to login."""
    if "username" in session:
        return redirect(url_for("board"))
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    GET:  Show the registration form.
    POST: Create a new user account with RSA keys and X.509 certificate.

    On successful registration:
      1. RSA-2048 key pair is generated
      2. Self-signed X.509 certificate is issued (username as CN)
      3. Private key is encrypted with the user's password and stored
      4. If this is the very first user, they become admin and a new
         AES group key is created for them automatically
      5. Otherwise they are a regular user with no group key yet —
         the admin must add them via the admin panel
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Basic validation
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("register.html")

        if get_user(username):
            flash("Username already taken.", "danger")
            return render_template("register.html")

        # --- Key generation ---
        private_key, public_key = generate_rsa_keypair()

        # Issue self-signed X.509 certificate
        cert = generate_certificate(username, private_key, public_key)
        cert_pem = serialize_certificate(cert)

        # Encrypt private key with the user's password before storage
        password_bytes = password.encode("utf-8")
        private_key_pem = serialize_private_key(private_key, password_bytes)

        # Hash the password for login verification (bcrypt, cost factor 12)
        password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12)).decode()

        # Determine if this is the first user (they become admin)
        all_users = get_all_users()
        is_first_user = len(all_users) == 0

        # Persist the user to the database
        create_user(
            username=username,
            password_hash=password_hash,
            private_key_pem=private_key_pem,
            certificate_pem=cert_pem,
            is_admin=is_first_user,
        )

        # If first user, create the group and give them the group key
        if is_first_user:
            from key_management import create_group
            from crypto import generate_aes_key
            aes_key = generate_aes_key()
            wrapped = wrap_group_key(aes_key, public_key)
            save_wrapped_key(username, wrapped, version=1)
            flash("Account created. You are the group admin!", "success")
        else:
            flash("Account created. Ask the admin to add you to the secure group.", "info")

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET:  Show the login form.
    POST: Verify password, decrypt the private key, unwrap the AES group key.

    The AES group key is unwrapped here and stored (as hex) in the
    session so subsequent requests can encrypt/decrypt without re-asking
    for the password.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_user(username)

        # Verify password against stored bcrypt hash
        if not user or not bcrypt.checkpw(
            password.encode("utf-8"),
            user.password_hash.encode("utf-8")
        ):
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        # Decrypt private key using the user's password
        try:
            private_key = deserialize_private_key(
                user.private_key,
                password.encode("utf-8")
            )
        except Exception:
            flash("Failed to decrypt private key. Wrong password?", "danger")
            return render_template("login.html")

        # Unwrap the AES group key (if the user is a group member)
        wrapped_key = get_wrapped_key(username)
        if wrapped_key:
            try:
                aes_key = unwrap_group_key(wrapped_key, private_key)
                # Store hex-encoded key in session for this session only
                session["aes_key_hex"] = binascii.hexlify(aes_key).decode()
            except ValueError:
                # User exists but key unwrap failed — re-key may have occurred
                flash("Could not load group key. Contact the admin.", "warning")

        # Store login state in session
        session["username"] = username
        session["is_admin"] = user.is_admin

        flash(f"Welcome back, {username}!", "success")
        return redirect(url_for("board"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear the session and redirect to login."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Board — view encrypted/decrypted pins
# ---------------------------------------------------------------------------

@app.route("/board")
@login_required
def board():
    """
    Fetch pins from Pinterest and attempt to decrypt each one.

    For each pin:
      - If the user has the AES group key AND the pin note looks like
        our ciphertext → decrypt and show plaintext
      - Otherwise → show the raw ciphertext (as any non-member would see)

    This is the core demonstration of the security model:
    members see plaintext, everyone else sees gibberish.
    """
    pinterest_token = session.get("pinterest_token")
    aes_key = get_aes_key_from_session()

    pins = []

    if pinterest_token:
        raw_pins = fetch_board_pins(pinterest_token)

        for pin in raw_pins:
            note = pin.get("note", "")
            pin_id = pin.get("id", "")

            # Attempt decryption if user has the group key
            if aes_key and is_encrypted(note):
                plaintext = decrypt_message(note, aes_key)
                display_text = plaintext if plaintext else f"[Encrypted] {note}"
                decrypted = plaintext is not None
            else:
                display_text = note
                decrypted = False

            pins.append({
                "id":         pin_id,
                "text":       display_text,
                "decrypted":  decrypted,
                "posted_by":  pin.get("creator", {}).get("username", "unknown"),
            })

            # Cache pin ID locally if not already stored
            if pin_id and not pin_exists(pin_id):
                save_pin(
                    pinterest_id=pin_id,
                    posted_by=pin.get("creator", {}).get("username", "unknown"),
                    board_id=pin.get("board_id", ""),
                )

    return render_template(
        "board.html",
        pins=pins,
        is_member=aes_key is not None,
        pinterest_connected=pinterest_token is not None,
        username=session["username"],
    )


# ---------------------------------------------------------------------------
# Post an encrypted pin
# ---------------------------------------------------------------------------

@app.route("/post", methods=["POST"])
@login_required
def post_pin():
    """
    Encrypt a message and post it as a Pinterest pin.

    Only group members (users with an AES key in their session) can post.
    The plaintext is encrypted with AES-256-GCM and the resulting
    Base64 ciphertext is sent to Pinterest as the pin description.
    """
    aes_key = get_aes_key_from_session()
    if not aes_key:
        flash("You are not a group member. Ask the admin to add you.", "warning")
        return redirect(url_for("board"))

    pinterest_token = session.get("pinterest_token")
    if not pinterest_token:
        flash("Connect your Pinterest account first.", "warning")
        return redirect(url_for("board"))

    message = request.form.get("message", "").strip()
    if not message:
        flash("Message cannot be empty.", "danger")
        return redirect(url_for("board"))

    # Encrypt the message
    ciphertext = encrypt_message(message, aes_key)

    # Post to Pinterest
    result = post_encrypted_pin(pinterest_token, ciphertext)
    if result:
        pin_id = result.get("id")
        if pin_id:
            save_pin(
                pinterest_id=pin_id,
                posted_by=session["username"],
                board_id=result.get("board_id", ""),
            )
        flash("Encrypted pin posted successfully!", "success")
    else:
        flash("Failed to post pin. Check Pinterest connection.", "danger")

    return redirect(url_for("board"))


# ---------------------------------------------------------------------------
# Pinterest OAuth2
# ---------------------------------------------------------------------------

@app.route("/connect")
@login_required
def connect_pinterest():
    """Redirect the user to Pinterest to authorise the app."""
    return redirect(get_authorisation_url())


@app.route("/callback")
@login_required
def pinterest_callback():
    """
    Handle the OAuth2 redirect from Pinterest.

    Pinterest redirects here with ?code=... after the user approves access.
    We exchange the code for an access token and store it in the session.
    """
    code = request.args.get("code")
    if not code:
        flash("Pinterest authorisation failed — no code received.", "danger")
        return redirect(url_for("board"))

    token_data = exchange_code_for_token(code)
    if not token_data:
        flash("Failed to get Pinterest access token.", "danger")
        return redirect(url_for("board"))

    session["pinterest_token"] = token_data["access_token"]
    flash("Pinterest connected successfully!", "success")
    return redirect(url_for("board"))


# ---------------------------------------------------------------------------
# Admin Panel
# ---------------------------------------------------------------------------

@app.route("/admin")
@login_required
@admin_required
def admin():
    """
    Display the admin panel.

    Shows:
      - All registered users and their group membership status
      - Form to add a user to the secure group
      - Form to remove a user (triggers a full re-key)
    """
    all_users = get_all_users()
    member_certs = get_all_member_certificates()

    # Build set of current member usernames for quick lookup in template
    member_usernames = set()
    for cert_pem in member_certs:
        cert = deserialize_certificate(cert_pem)
        member_usernames.add(get_username_from_cert(cert))

    return render_template(
        "admin.html",
        users=all_users,
        member_usernames=member_usernames,
        username=session["username"],
    )


@app.route("/admin/add", methods=["POST"])
@login_required
@admin_required
def admin_add_member():
    """
    Add a registered user to the secure group.

    Steps:
      1. Load the admin's AES group key from session
      2. Fetch the new member's X.509 certificate from the database
      3. Wrap the AES key with the new member's public key (from the cert)
      4. Store the wrapped key in the group_keys table

    The new member can now unwrap the group key at their next login.
    """
    target_username = request.form.get("username", "").strip()
    aes_key = get_aes_key_from_session()

    if not aes_key:
        flash("Admin session has no group key. Please log out and back in.", "danger")
        return redirect(url_for("admin"))

    target_user = get_user(target_username)
    if not target_user:
        flash(f"User '{target_username}' not found.", "danger")
        return redirect(url_for("admin"))

    # Check they are not already a member
    if get_wrapped_key(target_username):
        flash(f"'{target_username}' is already a group member.", "info")
        return redirect(url_for("admin"))

    try:
        # Wrap the current group key with the new member's public key
        wrapped = add_member(aes_key, target_user.certificate)
        save_wrapped_key(target_username, wrapped)
        flash(f"'{target_username}' has been added to the secure group.", "success")
    except ValueError as e:
        flash(f"Failed to add member: {e}", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/remove", methods=["POST"])
@login_required
@admin_required
def admin_remove_member():
    """
    Remove a user from the secure group and re-key the group.

    Steps:
      1. Delete the target user from the database entirely
      2. Fetch remaining members' certificates
      3. Generate a new AES group key
      4. Wrap the new key for each remaining member
      5. Save all new wrapped keys (old ones are overwritten)
      6. Update the admin's own session key to the new one

    After re-keying, the removed user's old wrapped key is gone.
    They cannot decrypt any future posts.
    """
    target_username = request.form.get("username", "").strip()

    if target_username == session["username"]:
        flash("You cannot remove yourself.", "danger")
        return redirect(url_for("admin"))

    # Delete the user and their group key entry
    if not delete_user(target_username):
        flash(f"User '{target_username}' not found.", "danger")
        return redirect(url_for("admin"))

    # Get remaining members' certificates for re-keying
    remaining_certs = get_all_member_certificates()

    if remaining_certs:
        # Generate new AES key and wrap for all remaining members
        new_aes_key, wrapped_keys = remove_member(remaining_certs)

        # Determine current key version and increment
        from database import get_current_key_version
        current_version = get_current_key_version(session["username"])
        new_version = current_version + 1

        # Persist new wrapped keys for all remaining members
        for uname, wkey in wrapped_keys.items():
            save_wrapped_key(uname, wkey, version=new_version)

        # Update admin's session with the new AES key
        session["aes_key_hex"] = binascii.hexlify(new_aes_key).decode()

        flash(
            f"'{target_username}' removed. Group re-keyed (v{new_version}). "
            f"All remaining members will receive the new key on next login.",
            "success"
        )
    else:
        flash(f"'{target_username}' removed. No members remain to re-key.", "info")

    return redirect(url_for("admin"))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # debug=True enables auto-reload on code changes during development.
    # NEVER run with debug=True in production.
    app.run(debug=True, port=5000)