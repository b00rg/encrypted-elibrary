from sqlalchemy import Column, Integer, String, Boolean, LargeBinary, DateTime
from datetime import datetime

class User(Base):
    __tablename__ = "users"  # MySQL table name

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    private_key = Column(LargeBinary, nullable=False)
    certificate = Column(LargeBinary, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<User username={self.username} is_admin={self.is_admin}>"
    
