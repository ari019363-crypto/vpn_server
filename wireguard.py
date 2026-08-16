import subprocess
import os
import re
import random
from config import Config
from typing import Tuple

# ============================================
# تولید کلید
# ============================================
def generate_keys() -> Tuple[str, str]:
    try:
        result = subprocess.run(['wg', 'genkey'], capture_output=True, text=True)
        private_key = result.stdout.strip()
        result = subprocess.run(['wg', 'pubkey'], input=private_key, capture_output=True, text=True)
        public_key = result.stdout.strip()
        return private_key, public_key
    except:
        # fallback
        import secrets
        private_key = secrets.token_hex(32)
        public_key = secrets.token_hex(32)
        return private_key, public_key

# ============================================
# تخصیص آی‌پی
# ============================================
def assign_ip() -> str:
    used_ips = []
    try:
        result = subprocess.run(['wg', 'show'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'allowed ips' in line.lower():
                ip = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip:
                    used_ips.append(ip.group(1))
    except:
        pass
    
    base = Config.WG_NETWORK.split('/')[0]
    base_parts = base.split('.')
    
    for i in range(2, 255):
        ip = f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.{i}"
        if ip not in used_ips:
            return ip
    return f"{base_parts[0]}.{base_parts[1]}.{base_parts[2]}.2"

# ============================================
# ساخت کانفیگ سرور
# ============================================
def generate_server_config(public_key: str) -> str:
    config = f"""
[Interface]
PrivateKey = {public_key}
Address = {Config.WG_NETWORK}
ListenPort = {Config.WG_PORT}
DNS = {Config.WG_DNS}
MTU = {Config.WG_MTU}

[Peer]
PublicKey = {public_key}
AllowedIPs = {Config.WG_NETWORK}
PersistentKeepalive = {Config.WG_PERSISTENT_KEEPALIVE}
"""
    return config

# ============================================
# اضافه کردن کاربر
# ============================================
def add_peer(public_key: str, ip_address: str, allowed_ips: str = None):
    if not allowed_ips:
        allowed_ips = ip_address + "/32"
    
    cmd = [
        'wg', 'set', Config.WG_INTERFACE,
        'peer', public_key,
        'allowed-ips', allowed_ips
    ]
    subprocess.run(cmd, capture_output=True)
    
    # ریلود
    subprocess.run(['wg-quick', 'save', Config.WG_INTERFACE])

# ============================================
# حذف کاربر
# ============================================
def remove_peer(public_key: str):
    cmd = ['wg', 'set', Config.WG_INTERFACE, 'peer', public_key, 'remove']
    subprocess.run(cmd, capture_output=True)
    subprocess.run(['wg-quick', 'save', Config.WG_INTERFACE])

# ============================================
# دریافت وضعیت
# ============================================
def get_status() -> dict:
    result = subprocess.run(['wg', 'show'], capture_output=True, text=True)
    return {
        'raw': result.stdout,
        'interface': Config.WG_INTERFACE,
        'port': Config.WG_PORT
    }

# ============================================
# ریستارت سرور
# ============================================
def restart_server():
    subprocess.run(['wg-quick', 'down', Config.WG_INTERFACE], capture_output=True)
    subprocess.run(['wg-quick', 'up', Config.WG_INTERFACE], capture_output=True)
