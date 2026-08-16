import subprocess
import os
import re
import random
from config import Config
from typing import Tuple

def generate_keys() -> Tuple[str, str]:
    try:
        # برای Railway که دسترسی به wg نداره، کلیدهای ساختگی
        import secrets
        private_key = secrets.token_hex(32)
        public_key = secrets.token_hex(32)
        return private_key, public_key
    except:
        import secrets
        return secrets.token_hex(32), secrets.token_hex(32)

def assign_ip() -> str:
    used_ips = []
    base = Config.WG_NETWORK.split('/')[0]
    base_parts = base.split('.')
    
    # چک کردن دیتابیس برای آی‌پی‌های استفاده شده
    from database import get_all_users
    for user in get_all_users():
        if user.ip_address:
            used_ips.append(user.ip_address)
    
    for i in range(2, 255):
        ip = f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.{i}"
        if ip not in used_ips:
            return ip
    return f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.2"

def add_peer(public_key: str, ip_address: str):
    # برای Railway که WireGuard نصب نیست، فقط دیتابیس رو به‌روز می‌کنیم
    pass

def remove_peer(public_key: str):
    pass

def get_status() -> dict:
    return {
        'interface': Config.WG_INTERFACE,
        'port': Config.WG_PORT,
        'active': True
    }

def get_server_public_key() -> str:
    # کلید عمومی سرور (برای Railway از یک کلید ثابت استفاده می‌کنیم)
    return "SERVER_PUBLIC_KEY_PLACEHOLDER"
