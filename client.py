import requests
import os
import json

class VPNClient:
    def __init__(self, server_url: str, username: str, password: str):
        self.server_url = server_url
        self.username = username
        self.password = password
        self.token = None
    
    def login(self) -> bool:
        try:
            response = requests.post(
                f"{self.server_url}/api/login",
                json={"username": self.username, "password": self.password}
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                return True
            return False
        except:
            return False
    
    def get_config(self, username: str = None) -> str:
        if not self.token:
            return None
        
        target = username or self.username
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.server_url}/api/user/{target}/config",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()["config"]
        return None
    
    def get_status(self) -> dict:
        if not self.token:
            return None
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.server_url}/api/status",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        return None

# ============================================
# استفاده
# ============================================
if __name__ == "__main__":
    client = VPNClient("http://localhost:8080", "admin", "your-password")
    if client.login():
        print("✅ Login successful")
        config = client.get_config()
        if config:
            print("📝 Config:\n", config)
        status = client.get_status()
        print("📊 Status:", status)
    else:
        print("❌ Login failed")
