from flask import jsonify, request, session

from app.routes import api
from app.crypto import decrypt_message, encrypt_message, generate_aes_key, is_encrypted
from app.database import (
    add_book, delete_global_book, get_all_books, get_all_users, get_global_book,
    get_owned_shelves, get_shelf_members,
)
from app.openlibrary import get_book, get_books_batch, search_books
from .helpers import _aes_key, _auth_required


@api.route("/shelf")
def shelf():
    err = _auth_required()
    if err:
        return err

    aes_key = _aes_key()
    books = []
    work_ids = []
    for b in get_all_books():
        work_id = None
        if aes_key and is_encrypted(b.work_id_enc):
            work_id = decrypt_message(b.work_id_enc, aes_key)
        entry = {
            "id": b.id,
            "work_id": work_id,
            "added_by": b.added_by,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "",
        }
        books.append(entry)
        if work_id:
            work_ids.append(work_id)

    if work_ids:
        meta = get_books_batch(work_ids)
        for entry in books:
            if entry["work_id"] and entry["work_id"] in meta:
                m = meta[entry["work_id"]]
                entry["title"] = m.get("title")
                entry["author"] = m.get("author")
                entry["cover_id"] = m.get("cover_id")
                entry["year"] = m.get("year")

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


@api.route("/shelf/books/<int:book_id>", methods=["DELETE"])
def shelf_delete_book(book_id: int):
    err = _auth_required()
    if err:
        return err

    book = get_global_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    if book.added_by != session["username"] and not session.get("is_admin"):
        return jsonify({"error": "Not authorized"}), 403

    delete_global_book(book_id)
    return jsonify({"message": "Book deleted"})


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

    admin_username = session["username"]
    owned_shelves = get_owned_shelves(admin_username)

    user_shelf_map: dict[str, list] = {}
    for shelf in owned_shelves:
        for m in get_shelf_members(shelf.id):
            user_shelf_map.setdefault(m.username, []).append(
                {"id": shelf.id, "name": shelf.name}
            )

    return jsonify({
        "users": [
            {
                "username": u.username,
                "is_admin": u.is_admin,
                "shelves": user_shelf_map.get(u.username, []),
            }
            for u in get_all_users()
        ]
    })
