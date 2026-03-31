import binascii

from flask import jsonify, session


def _aes_key() -> bytes | None:
    hex_key = session.get("aes_key_hex")
    return binascii.unhexlify(hex_key) if hex_key else None


def _shelf_key(shelf_id: int) -> bytes | None:
    hex_key = session.get("shelf_keys", {}).get(str(shelf_id))
    return binascii.unhexlify(hex_key) if hex_key else None


def _auth_required():
    if "username" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None
