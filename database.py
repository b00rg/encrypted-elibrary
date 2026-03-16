from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Integer, LargeBinary, String, create_engine)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///secure_pinterest.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

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


class Pin(Base):
    __tablename__ = "pins"
 
    id = Column(Integer, primary_key=True, autoincrement=True)
    pinterest_id = Column(String(128), unique=True, nullable=False)
    posted_by = Column(String(64), nullable=False)
    board_id = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
 
    def __repr__(self):
        return f"<Pin pinterest_id={self.pinterest_id} posted_by={self.posted_by}>"


def init_db():
    Base.metadata.create_all(bind=engine)


def create_user(username: str,
                password_hash: str,
                private_key_pem: bytes,
                certificate_pem: bytes,
                is_admin: bool = False) -> User:
    
    with SessionLocal as session:
        user = User(
            username = username,
            password_hash = password_hash,
            private_key_pem = private_key_pem,
            certificate_pem = certificate_pem,
            is_admin = is_admin
        )

        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def get_user(username: str) -> User | None:
    with SessionLocal as session:
        return session.query(User).filter_by(username=username).first()


def get_all_users() -> list[User]:
    with SessionLocal as session:
        return session.query(User).all


def delete_user(username: str) -> bool:
    with SessionLocal as session:
        user = session.query(User).filter_by(username=username).first()

        if not user:
            return False
        
        session.query(GroupKey).filter_by(username=username).delete()
        session.delete(user)
        session.commit()

        return True


def save_wrapped_key(username: str, wrapped_key: bytes, version: int = 1):
    with SessionLocal as session:
        existing = session.query(GroupKey).filter_by(username=username).first()

        if existing:
            existing.wrapped_key = wrapped_key
            existing.version = version
            existing.updated_at = datetime.now()
        else:
            session.add(GroupKey(
                username = username,
                wrapped_key = wrapped_key,
                version = version,
                updated_at = datetime.now()
            ))
        session.commit()


def get_wrapped_key(username: str) -> bytes | None:
    with SessionLocal as session:
        return session.query(GroupKey).filter_by(username=username).first()


def get_current_key_version(username: str) -> int:
    with SessionLocal as session:
        row = session.query(GroupKey).filter_by(username=username).first()
        return row.wrapped_key if row else None


def get_all_member_certificates() -> list[bytes]:
    with SessionLocal as session:
        members = (
            session.query(User),

        )
        return [m.certificate for m in members]


def save_pin(pinterest_id: str, posted_by: str, board_id: str) -> Pin:
    with SessionLocal as session:
        pin = Pin(
            pinterest_id=pinterest_id,
            posted_by=posted_by,
            board_id=board_id
        )
        session.add(pin)
        session.commit()
        session.refresh(pin)
        return pin


def get_all_pins() -> list[Pin]: 
    with SessionLocal as session:
        return session.query(Pin).all


def pin_exists(pinterest_id: str) -> bool:
    with SessionLocal as session:
        return session.query(Pin).filter_by(pinterest_id=pinterest_id).first() is not None