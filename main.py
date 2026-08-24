import os, hashlib, secrets
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

app = FastAPI(title="Nova Messenger")
users = {}
tokens = {}
connections = set()

def pw_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class Register(BaseModel):
    name: str
    email: EmailStr
    password: str

class Login(BaseModel):
    email: EmailStr
    password: str

HTML = r"""<!doctype html>
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
.tabs{display:flex;margin-bottom:18px}.tabs button{flex:1;background:none;border:0;color:#8995ab;padding:11px;border-bottom:2px solid transparent;cursor:pointer}
.tabs .on{color:#fff;border-color:#7c5cff}input{width:100%;padding:14px;margin:7px 0;background:#0b1220;color:#fff;border:1px solid #2c374d;border-radius:13px;outline:0}
.primary{width:100%;padding:14px;margin-top:10px;background:#7c5cff;border:0;border-radius:13px;color:#fff;font-weight:700;cursor:pointer}
.primary:active{transform:scale(.99)}.hint{color:#8995ab;text-align:center;font-size:13px;margin-top:14px}.error{color:#ff7d91;text-align:center;margin-top:10px;min-height:20px}
.chatapp{height:100dvh;display:flex;background:#0b1020}.sidebar{width:320px;background:#111827;border-right:1px solid #273247;padding:18px}.brand{font-size:24px;font-weight:800;margin:5px 4px 20px}.brand span{color:#7c5cff}
.user{padding:14px;background:#182236;border-radius:13px;margin-top:12px}.main{flex:1;display:flex;flex-direction:column}.head{height:70px;border-bottom:1px solid #273247;display:flex;align-items:center;padding:0 18px}.head b{flex:1}.head button{background:none;border:0;color:#fff;font-size:20px}
.msgs{flex:1;overflow:auto;padding:22px;display:flex;flex-direction:column;gap:10px}.msg{max-width:75%;padding:11px 14px;background:#182236;border-radius:16px}.mine{align-self:flex-end;background:#6f50e8}
.compose{padding:14px;border-top:1px solid #273247;display:flex;gap:8px}.compose input{flex:1}.send{width:48px;border:0;border-radius:13px;background:#7c5cff;color:#fff}
.welcome{margin:auto;text-align:center;color:#8792a8}@media(max-width:700px){.sidebar{display:none}.msg{max-width:86%}}
</style>
</head>
<body><div id="root"></div>
<script>
(function(){
const root=document.getElementById("root");
let token=localStorage.getItem("novaToken")||"";

function showAuth(){
 root.innerHTML=
 '<div class="screen"><div class="card">'+
 '<div class="logo">💬 <span>NOVA</span></div>'+
 '<div class="tabs"><button id="loginTab" class="on" type="button">Вход</button><button id="regTab" type="button">Регистрация</button></div>'+
 '<form id="authForm">'+
 '<input id="nameInput" placeholder="Имя" style="display:none">'+
 '<input id="emailInput" type="email" placeholder="Email" required>'+
 '<input id="passInput" type="password" placeholder="Пароль (минимум 6 символов)" minlength="6" required>'+
 '<button class="primary" id="submitBtn" type="submit">Войти</button></form>'+
 '<div class="error" id="errorBox"></div><div class="hint">Nova Messenger • тестовая версия</div>'+
 '</div></div>';

 const loginTab=document.getElementById("loginTab");
 const regTab=document.getElementById("regTab");
 const nameInput=document.getElementById("nameInput");
 const emailInput=document.getElementById("emailInput");
 const passInput=document.getElementById("passInput");
 const submitBtn=document.getElementById("submitBtn");
 const authForm=document.getElementById("authForm");
 const errorBox=document.getElementById("errorBox");
 let registerMode=false;

 function setMode(value){
   registerMode=value;
   nameInput.style.display=value?"block":"none";
   nameInput.required=value;
   submitBtn.textContent=value?"Создать аккаунт":"Войти";
   loginTab.className=value?"":"on";
   regTab.className=value?"on":"";
   errorBox.textContent="";
 }
 loginTab.addEventListener("click",function(){setMode(false)});
 regTab.addEventListener("click",function(){setMode(true)});

 authForm.addEventListener("submit",async function(e){
   e.preventDefault();
   errorBox.textContent="";
   submitBtn.disabled=true;
   submitBtn.textContent="Подождите…";
   try{
     const body=registerMode
       ? {name:nameInput.value.trim(),email:emailInput.value.trim(),password:passInput.value}
       : {email:emailInput.value.trim(),password:passInput.value};
     const response=await fetch(registerMode?"/api/register":"/api/login",{
       method:"POST",
       headers:{"Content-Type":"application/json"},
       body:JSON.stringify(body)
     });
     let data={};
     try{data=await response.json()}catch(_){}
     if(!response.ok) throw new Error(data.detail||("Ошибка сервера: "+response.status));
     localStorage.setItem("novaToken",data.access_token);
     location.reload();
   }catch(err){
     errorBox.textContent=err.message||"Не удалось выполнить запрос";
     submitBtn.textContent=registerMode?"Создать аккаунт":"Войти";
     submitBtn.disabled=false;
   }
 });
}

async function showChat(){
 const response=await fetch("/api/me",{headers:{"Authorization":"Bearer "+token}});
 if(!response.ok){localStorage.removeItem("novaToken");showAuth();return;}
 const me=await response.json();
 root.innerHTML=
 '<div class="chatapp"><aside class="sidebar"><div class="brand">💬 <span>NOVA</span></div>'+
 '<input id="searchInput" placeholder="Поиск">'+
 '<div class="user">👤 '+escapeHtml(me.name)+'<br><small>'+escapeHtml(me.email)+'</small></div></aside>'+
 '<main class="main"><header class="head"><b>Nova Messenger</b><button id="logoutBtn" type="button">↪</button></header>'+
 '<section class="msgs" id="messages"><div class="welcome">Nova подключён.<br>Откройте этот адрес на другом телефоне<br>и зарегистрируйте второй аккаунт.</div></section>'+
 '<form class="compose" id="chatForm"><input id="messageInput" placeholder="Написать сообщение…" autocomplete="off"><button class="send" type="submit">➤</button></form></main></div>';

 document.getElementById("logoutBtn").addEventListener("click",function(){
   localStorage.removeItem("novaToken");location.reload();
 });

 const messages=document.getElementById("messages");
 const messageInput=document.getElementById("messageInput");
 const chatForm=document.getElementById("chatForm");
 let ws;

 function connect(){
   ws=new WebSocket((location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws?token="+encodeURIComponent(token));
   ws.onmessage=function(e){
     const data=JSON.parse(e.data);
     if(data.type==="message"){
       const el=document.createElement("div");
       el.className="msg"+(data.mine?" mine":"");
       el.textContent=data.text;
       messages.appendChild(el);
       messages.scrollTop=messages.scrollHeight;
     }
   };
   ws.onclose=function(){setTimeout(connect,1500)};
 }
 chatForm.addEventListener("submit",function(e){
   e.preventDefault();
   const text=messageInput.value.trim();
   if(!text||!ws||ws.readyState!==WebSocket.OPEN)return;
   ws.send(JSON.stringify({text:text}));
   messageInput.value="";
 });
 connect();
}

function escapeHtml(s){return String(s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]})}
if(token)showChat();else showAuth();
})();
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HTML)

@app.get("/health")
async def health():
    return {"status":"ok","service":"nova"}

@app.post("/api/register")
async def register(x: Register):
    email = str(x.email).lower()
    name = x.name.strip()
    if not name:
        raise HTTPException(400, "Введите имя")
    if email in users:
        raise HTTPException(409, "Пользователь уже существует")
    if len(x.password) < 6:
        raise HTTPException(400, "Пароль должен быть минимум 6 символов")
    users[email] = {"name": name[:50], "password": pw_hash(x.password)}
    token = secrets.token_urlsafe(32)
    tokens[token] = email
    return {"access_token": token}

@app.post("/api/login")
async def login(x: Login):
    email = str(x.email).lower()
    user = users.get(email)
    if not user or user["password"] != pw_hash(x.password):
        raise HTTPException(401, "Неверный email или пароль")
    token = secrets.token_urlsafe(32)
    tokens[token] = email
    return {"access_token": token}

@app.get("/api/me")
async def me(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Нет авторизации")
    email = tokens.get(authorization[7:])
    if not email or email not in users:
        raise HTTPException(401, "Сессия недействительна")
    return {"name": users[email]["name"], "email": email}

@app.websocket("/ws")
async def websocket(ws: WebSocket, token: str):
    if token not in tokens:
        await ws.close(code=1008)
        return
    await ws.accept()
    connections.add(ws)
    try:
        while True:
            data = await ws.receive_json()
            text = str(data.get("text", "")).strip()
            if not text:
                continue
            for conn in list(connections):
                try:
                    await conn.send_json({"type":"message","text":text,"mine":conn is ws})
                except Exception:
                    connections.discard(conn)
    except WebSocketDisconnect:
        connections.discard(ws)
    except Exception:
        connections.discard(ws)
