from flask import jsonify, request, session

from app.routes import api
from app.crypto import decrypt_message, encrypt_message, is_encrypted
from app.database import (
    add_review, get_all_reviews_with_context, get_reviews, get_shelf, get_shelf_book,
    get_shelf_books, get_user_shelf_memberships,
)
from .helpers import _auth_required, _shelf_key


@api.route("/reviews/for-work")
def reviews_for_work():
    err = _auth_required()
    if err:
        return err

    work_id = request.args.get("work_id", "").strip()
    if not work_id:
        return jsonify({"error": "work_id required"}), 400

    username = session["username"]
    results = []
    for m in get_user_shelf_memberships(username):
        try:
            aes_key = _shelf_key(m.shelf_id)
            if not aes_key:
                continue
            shelf = get_shelf(m.shelf_id)
            if not shelf:
                continue
            for b in get_shelf_books(m.shelf_id):
                if not is_encrypted(b.work_id_enc):
                    continue
                if decrypt_message(b.work_id_enc, aes_key) != work_id:
                    continue
                shelf_reviews = []
                for r in get_reviews(b.id):
                    decrypted = decrypt_message(r.review_enc, aes_key) if is_encrypted(r.review_enc) else None
                    shelf_reviews.append({
                        "id": r.id,
                        "reviewer_username": r.reviewer_username,
                        "review": decrypted,
                        "review_enc": r.review_enc,
                        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                    })
                results.append({
                    "shelf_id": shelf.id,
                    "shelf_name": shelf.name,
                    "book_id": b.id,
                    "reviews": shelf_reviews,
                })
        except Exception:
            continue

    return jsonify({"results": results})


@api.route("/all-encrypted-reviews")
def all_encrypted_reviews():
    err = _auth_required()
    if err:
        return err

    username = session["username"]
    user_shelf_ids = {str(m.shelf_id) for m in get_user_shelf_memberships(username)}

    results = []
    for entry in get_all_reviews_with_context():
        shelf_id_str = str(entry["shelf_id"])
        is_member = shelf_id_str in user_shelf_ids
        aes_key = _shelf_key(entry["shelf_id"]) if is_member else None
        decrypted = None
        if aes_key and is_encrypted(entry["review_enc"]):
            decrypted = decrypt_message(entry["review_enc"], aes_key)
        results.append({
            "id": entry["review_id"],
            "shelf_id": entry["shelf_id"],
            "shelf_name": entry["shelf_name"],
            "book_id": entry["book_id"],
            "reviewer_username": entry["reviewer_username"],
            "review_enc": entry["review_enc"],
            "review": decrypted,
            "is_member": is_member,
            "created_at": entry["created_at"].strftime("%Y-%m-%d %H:%M") if entry["created_at"] else "",
        })

    return jsonify({"reviews": results})


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
