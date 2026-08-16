from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from config import Config
import hashlib
import secrets

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True)
    
    # WireGuard
    private_key = Column(String(255))
    public_key = Column(String(255))
    ip_address = Column(String(15))
    allowed_ips = Column(String(50))
    
    # محدودیت‌ها
    traffic_limit_gb = Column(Float, default=Config.DEFAULT_TRAFFIC_LIMIT_GB)
    traffic_used_gb = Column(Float, default=0.0)
    expire_date = Column(DateTime, default=lambda: datetime.now() + timedelta(days=Config.DEFAULT_EXPIRE_DAYS))
    
    # وضعیت
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    last_connected = Column(DateTime, nullable=True)
    
    def set_password(self, password: str):
        salt = secrets.token_hex(16)
        self.password_hash = hashlib.sha256((salt + password).encode()).hexdigest() + ":" + salt
    
    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        hash_part, salt = self.password_hash.split(":")
        return hash_part == hashlib.sha256((salt + password).encode()).hexdigest()

# ============================================
# توابع دیتابیس
# ============================================
def init_db():
    Base.metadata.create_all(engine)

def get_user(username: str):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    return user

def create_user(username: str, password: str, email: str = None) -> User:
    session = SessionLocal()
    user = User(username=username, email=email)
    user.set_password(password)
    
    # تولید کلیدهای WireGuard
    import wireguard
    private_key, public_key = wireguard.generate_keys()
    user.private_key = private_key
    user.public_key = public_key
    
    # آی‌پی
    session.add(user)
    session.commit()
    
    # تنظیم آی‌پی
    from wireguard import assign_ip
    user.ip_address = assign_ip()
    session.commit()
    
    session.close()
    return user

def delete_user(username: str):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    if user:
        # حذف از WireGuard
        import wireguard
        wireguard.remove_peer(user.public_key)
        session.delete(user)
        session.commit()
    session.close()

def update_traffic(username: str, bytes_used: int):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    if user:
        user.traffic_used_gb += bytes_used / (1024**3)
        session.commit()
    session.close()

def get_all_users():
    session = SessionLocal()
    users = session.query(User).all()
    session.close()
    return users
