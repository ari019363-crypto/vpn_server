#!/bin/bash

echo "🚀 Installing VPN Server..."

# نصب WireGuard
apt-get update
apt-get install wireguard wireguard-tools -y

# نصب Python
apt-get install python3 python3-pip -y

# نصب وابستگی‌ها
pip3 install -r requirements.txt

# ایجاد پوشه‌ها
mkdir -p /etc/wireguard/

# ایجاد کانفیگ اولیه
wg genkey | tee /etc/wireguard/private.key
wg pubkey < /etc/wireguard/private.key | tee /etc/wireguard/public.key

# تنظیم کانفیگ سرور
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/private.key)
Address = 10.0.0.1/24
ListenPort = 51820
DNS = 1.1.1.1, 8.8.8.8
MTU = 1420
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

# فعال‌سازی IP Forward
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

# اجرا
wg-quick up wg0
systemctl enable wg-quick@wg0

# اجرای سرور پایتون
python3 server.py

echo "✅ VPN Server installed successfully!"
echo "🌐 API: http://localhost:8080/docs"
