import os
from typing import Dict, Any

class Config:
    # سرور
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8080
    
    # WireGuard
    WG_INTERFACE = "wg0"
    WG_PORT = 51820
    WG_NETWORK = "10.0.0.0/24"
    WG_DNS = "1.1.1.1, 8.8.8.8"
    WG_MTU = 1420
    WG_PERSISTENT_KEEPALIVE = 25
    
    # دیتابیس
    DATABASE_URL = "sqlite:///vpn_users.db"
    
    # امنیت
    SECRET_KEY = "your-super-secret-key-change-this"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 ساعت
    
    # محدودیت‌ها
    MAX_USERS = 100
    DEFAULT_TRAFFIC_LIMIT_GB = 50
    DEFAULT_EXPIRE_DAYS = 30
    
    # مسیرها
    WG_CONFIG_DIR = "/etc/wireguard/"
    WG_QUICK_PATH = "/usr/bin/wg-quick"
    WG_PATH = "/usr/bin/wg"
    
    @classmethod
    def get_wg_config_path(cls, interface: str = WG_INTERFACE) -> str:
        return os.path.join(cls.WG_CONFIG_DIR, f"{interface}.conf")
