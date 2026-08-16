from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt
from config import Config
import database
import wireguard

app = FastAPI(title="VPN Manager", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ============================================
# مدل‌ها
# ============================================
class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    traffic_limit_gb: Optional[float] = 50
    expire_days: Optional[int] = 30

class UserResponse(BaseModel):
    username: str
    email: Optional[str]
    ip_address: str
    public_key: str
    traffic_limit_gb: float
    traffic_used_gb: float
    expire_date: str
    is_active: bool
    is_admin: bool
    created_at: str
    last_connected: Optional[str]

class ConfigResponse(BaseModel):
    config: str
    interface: str
    port: int

# ============================================
# توابع امنیتی
# ============================================
def create_token(username: str) -> str:
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        username = payload.get("username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def check_admin(username: str):
    user = database.get_user(username)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

# ============================================
# API
# ============================================

# --- احراز هویت ---
@app.post("/api/login")
async def login(request: LoginRequest):
    user = database.get_user(request.username)
    if not user or not user.verify_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")
    
    token = create_token(request.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": request.username,
        "is_admin": user.is_admin
    }

# --- مدیریت کاربران ---
@app.post("/api/admin/users", response_model=UserResponse)
async def create_user(request: CreateUserRequest, username: str = Depends(verify_token)):
    check_admin(username)
    
    if database.get_user(request.username):
        raise HTTPException(status_code=400, detail="User already exists")
    
    user = database.create_user(request.username, request.password, request.email)
    wireguard.add_peer(user.public_key, user.ip_address)
    
    return UserResponse(
        username=user.username,
        email=user.email,
        ip_address=user.ip_address,
        public_key=user.public_key,
        traffic_limit_gb=user.traffic_limit_gb,
        traffic_used_gb=user.traffic_used_gb,
        expire_date=user.expire_date.isoformat(),
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
        last_connected=user.last_connected.isoformat() if user.last_connected else None
    )

@app.get("/api/users")
async def get_users(username: str = Depends(verify_token)):
    check_admin(username)
    users = database.get_all_users()
    return [
        {
            "username": u.username,
            "ip_address": u.ip_address,
            "traffic_used_gb": round(u.traffic_used_gb, 2),
            "traffic_limit_gb": u.traffic_limit_gb,
            "is_active": u.is_active,
            "expire_date": u.expire_date.isoformat()
        }
        for u in users
    ]

@app.get("/api/user/{username}/config")
async def get_user_config(target_username: str, current_user: str = Depends(verify_token)):
    if current_user != target_username:
        check_admin(current_user)
    
    user = database.get_user(target_username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    config = f"""
[Interface]
PrivateKey = {user.private_key}
Address = {user.ip_address}/32
DNS = {Config.WG_DNS}
MTU = {Config.WG_MTU}

[Peer]
PublicKey = {wireguard.get_server_public_key()}
Endpoint = {Config.SERVER_HOST}:{Config.WG_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = {Config.WG_PERSISTENT_KEEPALIVE}
"""
    return {"config": config}

@app.post("/api/admin/user/{username}/toggle")
async def toggle_user(username: str, current_user: str = Depends(verify_token)):
    check_admin(current_user)
    user = database.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    # ذخیره در دیتابیس
    session = database.SessionLocal()
    session.merge(user)
    session.commit()
    session.close()
    
    return {"status": "updated", "is_active": user.is_active}

@app.delete("/api/admin/user/{username}")
async def delete_user(username: str, current_user: str = Depends(verify_token)):
    check_admin(current_user)
    database.delete_user(username)
    return {"status": "deleted"}

# --- وضعیت سرور ---
@app.get("/api/status")
async def get_status(username: str = Depends(verify_token)):
    status = wireguard.get_status()
    return {
        "interface": status['interface'],
        "port": status['port'],
        "active": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/config")
async def get_config(username: str = Depends(verify_token)):
    return {
        "interface": Config.WG_INTERFACE,
        "port": Config.WG_PORT,
        "network": Config.WG_NETWORK,
        "dns": Config.WG_DNS
    }

# ============================================
# اجرا
# ============================================
if __name__ == "__main__":
    import uvicorn
    print("🚀 VPN Server starting...")
    print("🌐 API: http://localhost:8080/docs")
    print("🔑 WireGuard Port:", Config.WG_PORT)
    uvicorn.run(app, host="0.0.0.0", port=8080)
