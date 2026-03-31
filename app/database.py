from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///bookshelf.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    private_key = Column(LargeBinary, nullable=False)
    certificate = Column(LargeBinary, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<User username={self.username} is_admin={self.is_admin}>"


class GroupKey(Base):
    __tablename__ = "group_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True)
    wrapped_key = Column(LargeBinary, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<GroupKey username={self.username} version={self.version}>"


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_id_enc = Column(Text, nullable=False)  # AES-GCM encrypted OpenLibrary work ID
    added_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Book added_by={self.added_by}>"


class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    owner_username = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Shelf id={self.id} name={self.name} owner={self.owner_username}>"


class ShelfMembership(Base):
    __tablename__ = "shelf_memberships"
    __table_args__ = (UniqueConstraint("shelf_id", "username"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    shelf_id = Column(Integer, nullable=False)
    username = Column(String(64), nullable=False)
    wrapped_key = Column(LargeBinary, nullable=False)
    key_version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<ShelfMembership shelf_id={self.shelf_id} username={self.username}>"


class ShelfBook(Base):
    __tablename__ = "shelf_books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shelf_id = Column(Integer, nullable=False)
    work_id_enc = Column(Text, nullable=False)
    added_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<ShelfBook shelf_id={self.shelf_id} added_by={self.added_by}>"


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shelf_book_id = Column(Integer, nullable=False)
    reviewer_username = Column(String(64), nullable=False)
    review_enc = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Review shelf_book_id={self.shelf_book_id} reviewer={self.reviewer_username}>"


def init_db():
    Base.metadata.create_all(bind=engine)


def create_user(username: str,
                password_hash: str,
                private_key_pem: bytes,
                certificate_pem: bytes,
                is_admin: bool = False) -> User:
    with SessionLocal() as session:
        user = User(
            username=username,
            password_hash=password_hash,
            private_key=private_key_pem,
            certificate=certificate_pem,
            is_admin=is_admin,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def get_user(username: str) -> User | None:
    with SessionLocal() as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            session.expunge(user)
        return user


def get_all_users() -> list[User]:
    with SessionLocal() as session:
        users = session.query(User).all()
        session.expunge_all()
        return users


def delete_user(username: str) -> bool:
    with SessionLocal() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return False
        session.query(GroupKey).filter_by(username=username).delete()
        session.delete(user)
        session.commit()
        return True


def save_wrapped_key(username: str, wrapped_key: bytes, version: int = 1):
    with SessionLocal() as session:
        existing = session.query(GroupKey).filter_by(username=username).first()
        if existing:
            existing.wrapped_key = wrapped_key
            existing.version = version
            existing.updated_at = datetime.now()
        else:
            session.add(GroupKey(
                username=username,
                wrapped_key=wrapped_key,
                version=version,
                updated_at=datetime.now(),
            ))
        session.commit()


def get_wrapped_key(username: str) -> bytes | None:
    with SessionLocal() as session:
        row = session.query(GroupKey).filter_by(username=username).first()
        return row.wrapped_key if row else None


def get_current_key_version(username: str) -> int:
    with SessionLocal() as session:
        row = session.query(GroupKey).filter_by(username=username).first()
        return row.version if row else 0


def get_all_member_certificates() -> list[bytes]:
    with SessionLocal() as session:
        members = (
            session.query(User)
            .join(GroupKey, User.username == GroupKey.username)
            .all()
        )
        return [m.certificate for m in members]


def add_book(work_id_enc: str, added_by: str) -> Book:
    with SessionLocal() as session:
        book = Book(work_id_enc=work_id_enc, added_by=added_by)
        session.add(book)
        session.commit()
        session.refresh(book)
        session.expunge(book)
        return book


def get_all_books() -> list[Book]:
    with SessionLocal() as session:
        books = session.query(Book).order_by(Book.created_at.desc()).all()
        session.expunge_all()
        return books


def get_global_book(book_id: int) -> Book | None:
    with SessionLocal() as session:
        book = session.query(Book).filter_by(id=book_id).first()
        if book:
            session.expunge(book)
        return book


def delete_global_book(book_id: int) -> bool:
    with SessionLocal() as session:
        book = session.query(Book).filter_by(id=book_id).first()
        if not book:
            return False
        session.delete(book)
        session.commit()
        return True


# --- Group Shelf ---

def create_shelf(name: str, owner_username: str) -> Shelf:
    with SessionLocal() as session:
        shelf = Shelf(name=name, owner_username=owner_username)
        session.add(shelf)
        session.commit()
        session.refresh(shelf)
        session.expunge(shelf)
        return shelf


def get_shelf(shelf_id: int) -> Shelf | None:
    with SessionLocal() as session:
        shelf = session.query(Shelf).filter_by(id=shelf_id).first()
        if shelf:
            session.expunge(shelf)
        return shelf


def get_user_shelves(username: str) -> list[Shelf]:
    with SessionLocal() as session:
        shelf_ids = [
            m.shelf_id for m in
            session.query(ShelfMembership).filter_by(username=username).all()
        ]
        if not shelf_ids:
            return []
        shelves = session.query(Shelf).filter(Shelf.id.in_(shelf_ids)).all()
        session.expunge_all()
        return shelves


def add_shelf_member(shelf_id: int, username: str, wrapped_key: bytes, version: int = 1):
    with SessionLocal() as session:
        existing = session.query(ShelfMembership).filter_by(
            shelf_id=shelf_id, username=username
        ).first()
        if existing:
            existing.wrapped_key = wrapped_key
            existing.key_version = version
            existing.updated_at = datetime.now()
        else:
            session.add(ShelfMembership(
                shelf_id=shelf_id, username=username,
                wrapped_key=wrapped_key, key_version=version,
            ))
        session.commit()


def get_shelf_member(shelf_id: int, username: str) -> ShelfMembership | None:
    with SessionLocal() as session:
        m = session.query(ShelfMembership).filter_by(
            shelf_id=shelf_id, username=username
        ).first()
        if m:
            session.expunge(m)
        return m


def get_shelf_members(shelf_id: int) -> list[ShelfMembership]:
    with SessionLocal() as session:
        members = session.query(ShelfMembership).filter_by(shelf_id=shelf_id).all()
        session.expunge_all()
        return members


def get_shelf_member_certificates(shelf_id: int) -> list[tuple[str, bytes]]:
    """Returns list of (username, certificate_pem) for all shelf members."""
    with SessionLocal() as session:
        members = session.query(ShelfMembership).filter_by(shelf_id=shelf_id).all()
        result = []
        for m in members:
            user = session.query(User).filter_by(username=m.username).first()
            if user:
                result.append((m.username, bytes(user.certificate)))
        return result


def remove_shelf_member(shelf_id: int, username: str) -> bool:
    with SessionLocal() as session:
        m = session.query(ShelfMembership).filter_by(
            shelf_id=shelf_id, username=username
        ).first()
        if not m:
            return False
        session.delete(m)
        session.commit()
        return True


def update_shelf_keys(shelf_id: int, wrapped_keys: dict, version: int):
    with SessionLocal() as session:
        for username, wrapped_key in wrapped_keys.items():
            m = session.query(ShelfMembership).filter_by(
                shelf_id=shelf_id, username=username
            ).first()
            if m:
                m.wrapped_key = wrapped_key
                m.key_version = version
                m.updated_at = datetime.now()
        session.commit()


def get_user_shelf_memberships(username: str) -> list[ShelfMembership]:
    with SessionLocal() as session:
        memberships = session.query(ShelfMembership).filter_by(username=username).all()
        session.expunge_all()
        return memberships


# --- Shelf Books ---

def add_shelf_book(shelf_id: int, work_id_enc: str, added_by: str) -> ShelfBook:
    with SessionLocal() as session:
        book = ShelfBook(shelf_id=shelf_id, work_id_enc=work_id_enc, added_by=added_by)
        session.add(book)
        session.commit()
        session.refresh(book)
        session.expunge(book)
        return book


def get_shelf_books(shelf_id: int) -> list[ShelfBook]:
    with SessionLocal() as session:
        books = session.query(ShelfBook).filter_by(shelf_id=shelf_id).order_by(
            ShelfBook.created_at.desc()
        ).all()
        session.expunge_all()
        return books


def get_shelf_book(book_id: int) -> ShelfBook | None:
    with SessionLocal() as session:
        book = session.query(ShelfBook).filter_by(id=book_id).first()
        if book:
            session.expunge(book)
        return book


# --- Reviews ---

def add_review(shelf_book_id: int, reviewer_username: str, review_enc: str) -> Review:
    with SessionLocal() as session:
        review = Review(
            shelf_book_id=shelf_book_id,
            reviewer_username=reviewer_username,
            review_enc=review_enc,
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        session.expunge(review)
        return review


def get_reviews(shelf_book_id: int) -> list[Review]:
    with SessionLocal() as session:
        reviews = session.query(Review).filter_by(shelf_book_id=shelf_book_id).order_by(
            Review.created_at.asc()
        ).all()
        session.expunge_all()
        return reviews


def delete_shelf_book(book_id: int) -> bool:
    with SessionLocal() as session:
        book = session.query(ShelfBook).filter_by(id=book_id).first()
        if not book:
            return False
        session.query(Review).filter_by(shelf_book_id=book_id).delete()
        session.delete(book)
        session.commit()
        return True


def get_all_reviews_with_context() -> list[dict]:
    """Returns all reviews with shelf/book context as plain dicts (safe to use outside session)."""
    with SessionLocal() as session:
        results = (
            session.query(Review, ShelfBook, Shelf)
            .join(ShelfBook, Review.shelf_book_id == ShelfBook.id)
            .join(Shelf, ShelfBook.shelf_id == Shelf.id)
            .order_by(Review.created_at.asc())
            .all()
        )
        output = []
        for review, shelf_book, shelf in results:
            output.append({
                "review_id": review.id,
                "shelf_book_id": review.shelf_book_id,
                "reviewer_username": review.reviewer_username,
                "review_enc": review.review_enc,
                "created_at": review.created_at,
                "shelf_id": shelf.id,
                "shelf_name": shelf.name,
                "shelf_owner": shelf.owner_username,
                "work_id_enc": shelf_book.work_id_enc,
                "book_id": shelf_book.id,
                "added_by": shelf_book.added_by,
            })
        return output
