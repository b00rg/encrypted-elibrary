import binascii

import bcrypt
from flask import Blueprint, jsonify, request, session

from app.crypto import decrypt_message, encrypt_message, generate_aes_key, is_encrypted
from app.database import (
    add_book, add_review, add_shelf_book, add_shelf_member, create_shelf, create_user,
    delete_user, get_all_books, get_all_member_certificates, get_all_users,
    get_current_key_version, get_reviews, get_shelf, get_shelf_book, get_shelf_books,
    get_shelf_member, get_shelf_member_certificates, get_shelf_members, get_user,
    get_user_shelf_memberships, get_user_shelves, get_wrapped_key, remove_shelf_member,
    save_wrapped_key, update_shelf_keys,
)
from app.key_management import (
    add_member, deserialize_certificate, deserialize_private_key,
    generate_certificate, generate_rsa_keypair, get_username_from_cert,
    remove_member, serialize_certificate, serialize_private_key,
    unwrap_group_key, wrap_group_key,
)
from app.openlibrary import get_book, search_books

api = Blueprint("api", __name__, url_prefix="/api")


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


@api.route("/shelf")
def shelf():
    err = _auth_required()
    if err:
        return err

    aes_key = _aes_key()
    books = []
    for b in get_all_books():
        work_id = None
        if aes_key and is_encrypted(b.work_id_enc):
            work_id = decrypt_message(b.work_id_enc, aes_key)
        books.append({
            "id": b.id,
            "work_id": work_id,
            "added_by": b.added_by,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "",
        })

    return jsonify({"books": books, "is_member": aes_key is not None})


@api.route("/shelf/add", methods=["POST"])
def shelf_add():
    err = _auth_required()
    if err:
        return err

    aes_key = _aes_key()
    if not aes_key:
        return jsonify({"error": "Not a shelf member"}), 403

    data = request.get_json() or {}
    work_id = data.get("work_id", "").strip()
    if not work_id:
        return jsonify({"error": "work_id required"}), 400

    work_id_enc = encrypt_message(work_id, aes_key)
    book = add_book(work_id_enc, session["username"])
    return jsonify({"id": book.id, "work_id": work_id, "added_by": book.added_by}), 201


@api.route("/shelf/search")
def shelf_search():
    err = _auth_required()
    if err:
        return err

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter required"}), 400

    return jsonify({"results": search_books(query)})


@api.route("/shelf/book/<work_id>")
def shelf_book(work_id: str):
    err = _auth_required()
    if err:
        return err

    book = get_book(work_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(book)


@api.route("/admin")
def admin():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    members = {
        get_username_from_cert(deserialize_certificate(cert_pem))
        for cert_pem in get_all_member_certificates()
    }
    return jsonify({
        "users": [
            {"username": u.username, "is_member": u.username in members, "is_admin": u.is_admin}
            for u in get_all_users()
        ]
    })


@api.route("/admin/add", methods=["POST"])
def admin_add():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    aes_key = _aes_key()
    if not aes_key:
        return jsonify({"error": "No group key in session"}), 400

    target = (request.get_json() or {}).get("username", "").strip()
    user = get_user(target)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if get_wrapped_key(target):
        return jsonify({"error": "Already a member"}), 400

    save_wrapped_key(target, add_member(aes_key, user.certificate))
    return jsonify({"message": f"{target} added to shelf"})


@api.route("/admin/remove", methods=["POST"])
def admin_remove():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    target = (request.get_json() or {}).get("username", "").strip()
    if target == session["username"]:
        return jsonify({"error": "Cannot remove yourself"}), 400
    if not delete_user(target):
        return jsonify({"error": "User not found"}), 404

    remaining = get_all_member_certificates()
    if remaining:
        new_key, wrapped_keys = remove_member(remaining)
        version = get_current_key_version(session["username"]) + 1
        for uname, wkey in wrapped_keys.items():
            save_wrapped_key(uname, wkey, version=version)
        session["aes_key_hex"] = binascii.hexlify(new_key).decode()

    return jsonify({"message": f"{target} removed and shelf re-keyed"})


# ---------------------------------------------------------------------------
# Group Shelves
# ---------------------------------------------------------------------------

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


@api.route("/shelves/<int:shelf_id>/members", methods=["GET"])
def list_shelf_members(shelf_id: int):
    err = _auth_required()
    if err:
        return err

    shelf = get_shelf(shelf_id)
    if not shelf:
        return jsonify({"error": "Shelf not found"}), 404
    if shelf.owner_username != session["username"]:
        return jsonify({"error": "Only the shelf owner can view members"}), 403

    members = get_shelf_members(shelf_id)
    return jsonify({
        "members": [
            {"username": m.username, "key_version": m.key_version}
            for m in members
        ]
    })


@api.route("/shelves/<int:shelf_id>/members", methods=["POST"])
def add_shelf_member_route(shelf_id: int):
    err = _auth_required()
    if err:
        return err

    shelf = get_shelf(shelf_id)
    if not shelf:
        return jsonify({"error": "Shelf not found"}), 404
    if shelf.owner_username != session["username"]:
        return jsonify({"error": "Only the shelf owner can add members"}), 403

    aes_key = _shelf_key(shelf_id)
    if not aes_key:
        return jsonify({"error": "No shelf key in session"}), 400

    target = (request.get_json() or {}).get("username", "").strip()
    user = get_user(target)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if get_shelf_member(shelf_id, target):
        return jsonify({"error": "Already a member"}), 400

    current_version = get_shelf_members(shelf_id)[0].key_version
    add_shelf_member(shelf_id, target, add_member(aes_key, user.certificate), version=current_version)
    return jsonify({"message": f"{target} added to shelf"})


@api.route("/shelves/<int:shelf_id>/members/<string:username>", methods=["DELETE"])
def remove_shelf_member_route(shelf_id: int, username: str):
    err = _auth_required()
    if err:
        return err

    shelf = get_shelf(shelf_id)
    if not shelf:
        return jsonify({"error": "Shelf not found"}), 404
    if shelf.owner_username != session["username"]:
        return jsonify({"error": "Only the shelf owner can remove members"}), 403
    if username == session["username"]:
        return jsonify({"error": "Cannot remove yourself"}), 400

    if not remove_shelf_member(shelf_id, username):
        return jsonify({"error": "User is not a member"}), 404

    remaining = get_shelf_member_certificates(shelf_id)
    if remaining:
        remaining_certs = [cert for _, cert in remaining]
        new_key, new_wrapped_keys = remove_member(remaining_certs)
        members = get_shelf_members(shelf_id)
        new_version = (members[0].key_version + 1) if members else 1
        update_shelf_keys(shelf_id, new_wrapped_keys, new_version)

        shelf_keys = session.get("shelf_keys", {})
        shelf_keys[str(shelf_id)] = binascii.hexlify(new_key).decode()
        session["shelf_keys"] = shelf_keys

    return jsonify({"message": f"{username} removed and shelf re-keyed"})


# ---------------------------------------------------------------------------
# Book Club Reviews (encrypted with shelf key)
# ---------------------------------------------------------------------------

@api.route("/shelves/<int:shelf_id>/books/<int:book_id>/reviews", methods=["GET"])
def get_book_reviews(shelf_id: int, book_id: int):
    err = _auth_required()
    if err:
        return err

    aes_key = _shelf_key(shelf_id)
    if not aes_key:
        return jsonify({"error": "Not a member of this shelf"}), 403

    book = get_shelf_book(book_id)
    if not book or book.shelf_id != shelf_id:
        return jsonify({"error": "Book not found on this shelf"}), 404

    reviews = get_reviews(book_id)
    return jsonify({
        "reviews": [
            {
                "id": r.id,
                "reviewer_username": r.reviewer_username,
                "review": decrypt_message(r.review_enc, aes_key) if is_encrypted(r.review_enc) else None,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in reviews
        ]
    })


@api.route("/shelves/<int:shelf_id>/books/<int:book_id>/reviews", methods=["POST"])
def post_review(shelf_id: int, book_id: int):
    err = _auth_required()
    if err:
        return err

    aes_key = _shelf_key(shelf_id)
    if not aes_key:
        return jsonify({"error": "Not a member of this shelf"}), 403

    book = get_shelf_book(book_id)
    if not book or book.shelf_id != shelf_id:
        return jsonify({"error": "Book not found on this shelf"}), 404

    review_text = (request.get_json() or {}).get("review", "").strip()
    if not review_text:
        return jsonify({"error": "Review text required"}), 400

    review = add_review(book_id, session["username"], encrypt_message(review_text, aes_key))
    return jsonify({
        "id": review.id,
        "reviewer_username": review.reviewer_username,
        "review": review_text,
        "created_at": review.created_at.strftime("%Y-%m-%d %H:%M") if review.created_at else "",
    }), 201
