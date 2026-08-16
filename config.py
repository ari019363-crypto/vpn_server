import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # تلگرام
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8949444239:AAFMb3M8XGMShXYWb3VLwHhu7pbo34RvXXI")
    OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
    
    # سرور
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", 8080))
    PUBLIC_IP = os.getenv("PUBLIC_IP", "your-server-ip.railway.app")  # آدرس عمومی
    
    # WireGuard
    WG_INTERFACE = os.getenv("WG_INTERFACE", "wg0")
    WG_PORT = int(os.getenv("WG_PORT", 51820))
    WG_NETWORK = os.getenv("WG_NETWORK", "10.0.0.0/24")
    WG_DNS = os.getenv("WG_DNS", "1.1.1.1, 8.8.8.8")
    WG_MTU = int(os.getenv("WG_MTU", 1420))
    WG_PERSISTENT_KEEPALIVE = int(os.getenv("WG_PERSISTENT_KEEPALIVE", 25))
    
    # دیتابیس
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vpn_users.db")
    
    # محدودیت‌ها
    DEFAULT_TRAFFIC_GB = float(os.getenv("DEFAULT_TRAFFIC_GB", 50))
    DEFAULT_EXPIRE_DAYS = int(os.getenv("DEFAULT_EXPIRE_DAYS", 30))
    MAX_USERS = int(os.getenv("MAX_USERS", 100))
