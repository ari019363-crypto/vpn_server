from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
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
    password_hash = Column(String(255))
    email = Column(String(100))
    
    # WireGuard
    private_key = Column(String(255))
    public_key = Column(String(255))
    ip_address = Column(String(15))
    
    # محدودیت‌ها
    traffic_limit_gb = Column(Float, default=Config.DEFAULT_TRAFFIC_GB)
    traffic_used_gb = Column(Float, default=0.0)
    expire_date = Column(DateTime, default=lambda: datetime.now() + timedelta(days=Config.DEFAULT_EXPIRE_DAYS))
    
    # وضعیت
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    last_connected = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    def set_password(self, password: str):
        salt = secrets.token_hex(16)
        self.password_hash = hashlib.sha256((salt + password).encode()).hexdigest() + ":" + salt
    
    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        hash_part, salt = self.password_hash.split(":")
        return hash_part == hashlib.sha256((salt + password).encode()).hexdigest()

class TrafficLog(Base):
    __tablename__ = "traffic_logs"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    bytes_sent = Column(Float, default=0)
    bytes_received = Column(Float, default=0)
    timestamp = Column(DateTime, default=datetime.now)

def init_db():
    Base.metadata.create_all(engine)

def get_user(username: str):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    return user

def get_all_users():
    session = SessionLocal()
    users = session.query(User).all()
    session.close()
    return users

def get_active_users():
    session = SessionLocal()
    users = session.query(User).filter_by(is_active=True).all()
    session.close()
    return users

def create_user(username: str, password: str, email: str = None, traffic_gb: float = None, expire_days: int = None) -> User:
    session = SessionLocal()
    
    user = User(username=username, email=email)
    user.set_password(password)
    
    # تولید کلیدهای WireGuard
    import wireguard
    private_key, public_key = wireguard.generate_keys()
    user.private_key = private_key
    user.public_key = public_key
    user.ip_address = wireguard.assign_ip()
    
    if traffic_gb:
        user.traffic_limit_gb = traffic_gb
    if expire_days:
        user.expire_date = datetime.now() + timedelta(days=expire_days)
    
    session.add(user)
    session.commit()
    session.close()
    return user

def update_user(username: str, **kwargs):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    if user:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        session.commit()
    session.close()

def delete_user(username: str):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    if user:
        import wireguard
        wireguard.remove_peer(user.public_key)
        session.delete(user)
        session.commit()
    session.close()

def add_traffic_log(username: str, sent: float, received: float):
    session = SessionLocal()
    log = TrafficLog(username=username, bytes_sent=sent, bytes_received=received)
    session.add(log)
    session.commit()
    session.close()
