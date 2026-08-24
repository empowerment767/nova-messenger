import os, hashlib, secrets, json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

app = FastAPI(title="Nova Messenger")
users = {}
tokens = {}
connections = set()

def pw_hash(p):
    return hashlib.sha256(p.encode()).hexdigest()

def page():
    return r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0b1020">
<title>Nova Messenger</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#fff;font-family:system-ui,-apple-system,Segoe UI,sans-serif}
button,input{font:inherit}.screen{min-height:100dvh;display:grid;place-items:center;padding:20px}
.card{width:min(430px,100%);background:#111827;border:1px solid #273247;border-radius:24px;padding:28px;box-shadow:0 20px 70px #0007}
.logo{text-align:center;font-size:30px;font-weight:800;margin-bottom:22px}.logo span{color:#7c5cff}
.tabs{display:flex;margin-bottom:18px}.tabs button{flex:1;background:none;border:0;color:#8995ab;padding:11px;border-bottom:2px solid transparent}.tabs .on{color:#fff;border-color:#7c5cff}
input{width:100%;padding:14px;margin:7px 0;background:#0b1220;color:#fff;border:1px solid #2c374d;border-radius:13px;outline:0}
.primary{width:100%;padding:14px;margin-top:10px;background:#7c5cff;border:0;border-radius:13px;color:#fff;font-weight:700}
.hint{color:#8995ab;text-align:center;font-size:13px;margin-top:14px}.error{color:#ff7d91;text-align:center;margin-top:10px;min-height:20px}
.chatapp{height:100dvh;display:flex;background:#0b1020}.sidebar{width:320px;background:#111827;border-right:1px solid #273247;padding:18px}.brand{font-size:24px;font-weight:800;margin:5px 4px 20px}.brand span{color:#7c5cff}
.user{padding:14px;background:#182236;border-radius:13px;margin-top:12px}.main{flex:1;display:flex;flex-direction:column}.head{height:70px;border-bottom:1px solid #273247;display:flex;align-items:center;padding:0 18px}.head b{flex:1}.head button{background:none;border:0;color:#fff;font-size:20px}
.msgs{flex:1;overflow:auto;padding:22px;display:flex;flex-direction:column;gap:10px}.msg{max-width:75%;padding:11px 14px;background:#182236;border-radius:16px}.mine{align-self:flex-end;background:#6f50e8}
.compose{padding:14px;border-top:1px solid #273247;display:flex;gap:8px}.compose input{flex:1}.send{width:48px;border:0;border-radius:13px;background:#7c5cff;color:#fff}
.welcome{margin:auto;text-align:center;color:#8792a8}@media(max-width:700px){.sidebar{display:none}.msg{max-width:86%}}
</style>
</head>
<body>
<div id="root"></div>
<script>
let token=localStorage.novaToken||"";
const root=document.getElementById("root");
function auth(){
root.innerHTML=`<div class="screen"><div class="card"><div class="logo">💬 <span>NOVA</span></div>
<div class="tabs"><button id="l" class="on">Вход</button><button id="r">Регистрация</button></div>
<form id="f"><input id="name" placeholder="Имя" style="display:none"><input id="email" type="email" placeholder="Email" required><input id="pass" type="password" placeholder="Пароль" required><button class="primary" id="go">Войти</button></form>
<div class="error" id="err"></div><div class="hint">Nova Messenger • тестовая версия</div></div></div>`;
let reg=false;
function mode(x){reg=x;name.style.display=x?"block":"none";name.required=x;go.textContent=x?"Создать аккаунт":"Войти";l.className=x?"":"on";r.className=x?"on":"";err.textContent=""}
l.onclick=()=>mode(false);r.onclick=()=>mode(true);
f.onsubmit=async e=>{e.preventDefault();err.textContent="";
let body=reg?{name:name.value,email:email.value,password:pass.value}:{email:email.value,password:pass.value};
try{let q=await fetch(reg?"/api/register":"/api/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),d=await q.json();if(!q.ok)throw Error(d.detail||"Ошибка");localStorage.novaToken=d.access_token;location.reload()}catch(x){err.textContent=x.message}}
}
async function chat(){
let q=await fetch("/api/me",{headers:{Authorization:"Bearer "+token}});if(!q.ok){localStorage.removeItem("novaToken");return auth()}
let me=await q.json();
root.innerHTML=`<div class="chatapp"><aside class="sidebar"><div class="brand">💬 <span>NOVA</span></div><input placeholder="Поиск"><div class="user">👤 ${me.name}<br><small>${me.email}</small></div></aside>
<main class="main"><header class="head"><b>Nova Messenger</b><button id="out">↪</button></header><section class="msgs" id="msgs"><div class="welcome">Nova подключён.<br>Откройте этот адрес на другом телефоне<br>и зарегистрируйте второй аккаунт.</div></section>
<form class="compose" id="cf"><input id="txt" placeholder="Написать сообщение…" autocomplete="off"><button class="send">➤</button></form></main></div>`;
out.onclick=()=>{localStorage.removeItem("novaToken");location.reload()};
let ws=new WebSocket((location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws?token="+encodeURIComponent(token));
ws.onmessage=e=>{let d=JSON.parse(e.data);if(d.type==="message"){let x=document.createElement("div");x.className="msg"+(d.mine?" mine":"");x.textContent=d.text;msgs.appendChild(x);msgs.scrollTop=msgs.scrollHeight}};
cf.onsubmit=e=>{e.preventDefault();if(txt.value.trim()&&ws.readyState===1){ws.send(JSON.stringify({text:txt.value.trim()}));txt.value=""}}
}
token?chat():auth();
</script>
</body></html>"""

class Register(BaseModel):
    name: str
    email: EmailStr
    password: str

class Login(BaseModel):
    email: EmailStr
    password: str

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(page())

@app.get("/health")
async def health():
    return {"status":"ok","service":"nova"}

@app.post("/api/register")
async def register(x:Register):
    email=x.email.lower()
    if email in users:
        raise HTTPException(409,"Пользователь уже существует")
    if len(x.password)<6:
        raise HTTPException(400,"Пароль должен быть минимум 6 символов")
    users[email]={"name":x.name[:50],"password":pw_hash(x.password)}
    token=secrets.token_urlsafe(32)
    tokens[token]=email
    return {"access_token":token}

@app.post("/api/login")
async def login(x:Login):
    email=x.email.lower()
    u=users.get(email)
    if not u or u["password"]!=pw_hash(x.password):
        raise HTTPException(401,"Неверный email или пароль")
    token=secrets.token_urlsafe(32)
    tokens[token]=email
    return {"access_token":token}

@app.get("/api/me")
async def me(authorization:str|None=None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Нет авторизации")
    email=tokens.get(authorization[7:])
    if not email:
        raise HTTPException(401,"Сессия недействительна")
    return {"name":users[email]["name"],"email":email}

@app.websocket("/ws")
async def websocket(ws:WebSocket, token:str):
    if token not in tokens:
        await ws.close(code=1008)
        return
    await ws.accept()
    connections.add(ws)
    try:
        while True:
            data=await ws.receive_json()
            text=str(data.get("text","")).strip()
            if not text:
                continue
            for c in list(connections):
                try:
                    await c.send_json({"type":"message","text":text,"mine":c is ws})
                except:
                    connections.discard(c)
    except WebSocketDisconnect:
        connections.discard(ws)
    except:
        connections.discard(ws)
