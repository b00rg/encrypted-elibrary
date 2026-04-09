import binascii

import bcrypt
from flask import jsonify, request, session

from app.routes import api
from app.crypto import generate_aes_key
from app.database import (
    create_user, get_all_users, get_user, get_user_shelf_memberships,
    get_wrapped_key, save_wrapped_key,
)
from app.key_management import (
    deserialize_private_key, generate_certificate, generate_rsa_keypair,
    serialize_certificate, serialize_private_key, unwrap_group_key, wrap_group_key,
)


@api.route("/me")
def me():
    if "username" not in session:
        return jsonify(None), 200
    return jsonify({"username": session["username"], "is_admin": session.get("is_admin", False)})


@api.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if get_user(username):
        return jsonify({"error": "Username already taken"}), 409

    private_key, public_key = generate_rsa_keypair()
    cert_pem = serialize_certificate(generate_certificate(username, private_key, public_key))
    pw_bytes = password.encode()
    is_first = len(get_all_users()) == 0

    create_user(
        username=username,
        password_hash=bcrypt.hashpw(pw_bytes, bcrypt.gensalt(12)).decode(),
        private_key_pem=serialize_private_key(private_key, pw_bytes),
        certificate_pem=cert_pem,
        is_admin=is_first,
    )

    if is_first:
        aes_key = generate_aes_key()
        save_wrapped_key(username, wrap_group_key(aes_key, public_key), version=1)

    return jsonify({"message": "Registered", "is_admin": is_first}), 201


@api.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = get_user(username)
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({"error": "Invalid username or password"}), 401

    try:
        private_key = deserialize_private_key(user.private_key, password.encode())
    except Exception:
        return jsonify({"error": "Failed to decrypt private key"}), 401

    wrapped = get_wrapped_key(username)
    if wrapped:
        try:
            aes_key = unwrap_group_key(wrapped, private_key)
            session["aes_key_hex"] = binascii.hexlify(aes_key).decode()
        except ValueError:
            pass

    shelf_keys = {}
    for m in get_user_shelf_memberships(username):
        try:
            shelf_aes = unwrap_group_key(m.wrapped_key, private_key)
            shelf_keys[str(m.shelf_id)] = binascii.hexlify(shelf_aes).decode()
        except ValueError:
            pass
    session["shelf_keys"] = shelf_keys

    session["username"] = username
    session["is_admin"] = user.is_admin
    return jsonify({"username": username, "is_admin": user.is_admin})


@api.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})
