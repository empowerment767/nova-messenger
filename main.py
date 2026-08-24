import os, hashlib, secrets, json, time
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

app=FastAPI(title="Nova Messenger API")
app.mount("/static",StaticFiles(directory="static"),name="static")

# Demo persistence for first Render deployment.
# Replace with PostgreSQL in the next stage.
users={}
tokens={}
connections=set()

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()
def user_by_token(t): return tokens.get(t)
class Register(BaseModel): name:str; email:EmailStr; password:str
class Login(BaseModel): email:EmailStr; password:str
class Message(BaseModel): text:str

@app.get("/")
async def root(): return FileResponse("static/index.html")
@app.get("/chat")
async def chat(): return FileResponse("static/chat.html")
@app.get("/health")
async def health(): return {"status":"ok","service":"nova"}

@app.post("/api/register")
async def register(x:Register):
    email=x.email.lower()
    if email in users: raise HTTPException(409,"Пользователь уже существует")
    if len(x.password)<6: raise HTTPException(400,"Пароль должен быть минимум 6 символов")
    users[email]={"name":x.name[:50],"email":email,"password":hash_pw(x.password)}
    t=secrets.token_urlsafe(32);tokens[t]=email
    return {"access_token":t,"token_type":"bearer"}

@app.post("/api/login")
async def login(x:Login):
    email=x.email.lower();u=users.get(email)
    if not u or u["password"]!=hash_pw(x.password): raise HTTPException(401,"Неверный email или пароль")
    t=secrets.token_urlsafe(32);tokens[t]=email
    return {"access_token":t,"token_type":"bearer"}

@app.get("/api/me")
async def me(authorization:str|None=Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401,"Нет авторизации")
    email=user_by_token(authorization[7:])
    if not email or email not in users: raise HTTPException(401,"Сессия недействительна")
    return {"name":users[email]["name"],"email":email}

@app.websocket("/ws")
async def ws(socket:WebSocket,token:str):
    email=user_by_token(token)
    if not email: await socket.close(code=1008); return
    await socket.accept();connections.add(socket)
    try:
        await socket.send_json({"type":"system","text":"Подключено к Nova"})
        while True:
            data=await socket.receive_json();text=str(data.get("text","")).strip()
            if not text: continue
            for c in list(connections):
                try: await c.send_json({"type":"message","text":text,"mine":c is socket})
                except: connections.discard(c)
    except WebSocketDisconnect: connections.discard(socket)
    except Exception: connections.discard(socket)
