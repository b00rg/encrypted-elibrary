import binascii

from flask import jsonify, request, session

from app.routes import api
from app.crypto import decrypt_message, encrypt_message, generate_aes_key, is_encrypted
from app.database import (
    add_shelf_book, add_shelf_member, create_shelf, get_shelf, get_shelf_books,
    get_user, get_user_shelves,
)
from app.key_management import deserialize_certificate, wrap_group_key
from .helpers import _auth_required, _shelf_key


@api.route("/shelves", methods=["GET"])
def list_shelves():
    err = _auth_required()
    if err:
        return err

    username = session["username"]
    shelves = get_user_shelves(username)
    return jsonify({
        "shelves": [
            {
                "id": s.id,
                "name": s.name,
                "owner_username": s.owner_username,
                "is_owner": s.owner_username == username,
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            }
            for s in shelves
        ]
    })


@api.route("/shelves", methods=["POST"])
def create_shelf_route():
    err = _auth_required()
    if err:
        return err

    name = (request.get_json() or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "Shelf name required"}), 400

    username = session["username"]
    user = get_user(username)
    cert = deserialize_certificate(user.certificate)
    creator_public_key = cert.public_key()

    aes_key = generate_aes_key()
    wrapped_key = wrap_group_key(aes_key, creator_public_key)

    shelf = create_shelf(name, username)
    add_shelf_member(shelf.id, username, wrapped_key, version=1)

    shelf_keys = session.get("shelf_keys", {})
    shelf_keys[str(shelf.id)] = binascii.hexlify(aes_key).decode()
    session["shelf_keys"] = shelf_keys

    return jsonify({
        "id": shelf.id,
        "name": shelf.name,
        "owner_username": shelf.owner_username,
    }), 201


@api.route("/shelves/<int:shelf_id>/books", methods=["GET"])
def list_shelf_books(shelf_id: int):
    err = _auth_required()
    if err:
        return err

    aes_key = _shelf_key(shelf_id)
    if not aes_key:
        return jsonify({"error": "Not a member of this shelf"}), 403

    shelf = get_shelf(shelf_id)
    if not shelf:
        return jsonify({"error": "Shelf not found"}), 404

    books = get_shelf_books(shelf_id)
    result = []
    for b in books:
        work_id = decrypt_message(b.work_id_enc, aes_key) if is_encrypted(b.work_id_enc) else None
        result.append({
            "id": b.id,
            "work_id": work_id,
            "added_by": b.added_by,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "",
        })

    return jsonify({
        "shelf": {"id": shelf.id, "name": shelf.name, "owner_username": shelf.owner_username},
        "books": result,
    })


@api.route("/shelves/<int:shelf_id>/books", methods=["POST"])
def add_book_to_shelf(shelf_id: int):
    err = _auth_required()
    if err:
        return err

    aes_key = _shelf_key(shelf_id)
    if not aes_key:
        return jsonify({"error": "Not a member of this shelf"}), 403

    work_id = (request.get_json() or {}).get("work_id", "").strip()
    if not work_id:
        return jsonify({"error": "work_id required"}), 400

    book = add_shelf_book(shelf_id, encrypt_message(work_id, aes_key), session["username"])
    return jsonify({"id": book.id, "work_id": work_id, "added_by": book.added_by}), 201
