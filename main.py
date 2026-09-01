from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
import hashlib

app = FastAPI()

# MongoDB Atlas Bağlantı Adresin
MONGO_URL = "mongodb+srv://realsaatyilmaz:Yilmaz1234@yilmazbrawl.mtjhdek.mongodb.net/?appName=YilmazBrawl"

client = AsyncIOMotorClient(
    MONGO_URL,
    tls=True,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=5000
)

db = client["my_firebase"]
collection = db["store"]
users_db = db["users"]

# --- 1. KULLANICI ARAYÜZÜ (GİRİŞ / KAYIT / KOPYALA BUTONLU PANEL) ---
@app.get("/", response_class=HTMLResponse)
async def home_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>AeroBase Dashboard</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #1e1e1e; padding: 30px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); width: 350px; text-align: center; }
            h2 { margin-bottom: 20px; color: #00e676; }
            input { width: 90%; padding: 10px; margin: 8px 0; border-radius: 6px; border: 1px solid #333; background: #2a2a2a; color: #fff; }
            button { width: 95%; padding: 12px; margin-top: 10px; border-radius: 6px; border: none; background: #00e676; color: #121212; font-weight: bold; cursor: pointer; font-size: 15px; }
            button:hover { background: #00c853; }
            .copy-btn { background: #29b6f6; color: #121212; margin-top: 15px; }
            .copy-btn:hover { background: #03a9f4; }
            .project-box { display: none; margin-top: 20px; background: #2a2a2a; padding: 15px; border-radius: 8px; border: 1px dashed #00e676; }
            .url-text { color: #80d8ff; font-size: 14px; margin-top: 10px; background: #121212; padding: 10px; border-radius: 6px; word-break: break-all; }
        </style>
    </head>
    <body>
        <div class="card" id="authBox">
            <h2>AeroBase Panel</h2>
            <input type="text" id="username" placeholder="Kullanıcı Adı">
            <input type="password" id="password" placeholder="Şifre">
            <button onclick="login()">Giriş Yap / Kaydol</button>
            <p id="msg" style="color: #ff5252; font-size: 13px;"></p>
        </div>

        <div class="card" id="dashboardBox" style="display:none;">
            <h2 id="welcomeText">Hoşgeldin!</h2>
            <button onclick="createProject()">+ Create Project</button>
            
            <div id="projectResult" class="project-box">
                <small style="color:#aaa;">Proje Key:</small>
                <h4 id="projKey" style="color:#00e676; margin: 5px 0;"></h4>
                <small style="color:#aaa;">Base API Linkin:</small>
                <div id="projUrl" class="url-text"></div>
                <button class="copy-btn" onclick="copyUrl()">📋 URL Kopyala</button>
                <p id="copyMsg" style="color: #00e676; font-size: 13px; display: none; margin-top: 10px;">Bağlantı kopyalandı!</p>
            </div>
        </div>

        <script>
            let currentUrl = "";

            async function login() {
                const u = document.getElementById('username').value;
                const p = document.getElementById('password').value;
                if(!u || !p) { document.getElementById('msg').innerText = 'Lütfen alanları doldurun!'; return; }
                
                const res = await fetch('/api/auth', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p})
                });
                const data = await res.json();
                if(data.status === 'ok') {
                    document.getElementById('authBox').style.display = 'none';
                    document.getElementById('dashboardBox').style.display = 'block';
                    document.getElementById('welcomeText').innerText = 'Hoş geldin, ' + u;
                }
            }

            async function createProject() {
                const res = await fetch('/api/create-project', { method: 'POST' });
                const data = await res.json();
                document.getElementById('projectResult').style.display = 'block';
                document.getElementById('projKey').innerText = data.project_key;
                
                // Sadece sonu / ile biten temel URL'i veriyoruz
                currentUrl = 'https://aerobase.onrender.com/' + data.project_key + '/';
                document.getElementById('projUrl').innerText = currentUrl;
            }

            function copyUrl() {
                navigator.clipboard.writeText(currentUrl);
                document.getElementById('copyMsg').style.display = 'block';
                setTimeout(() => { document.getElementById('copyMsg').style.display = 'none'; }, 2000);
            }
        </script>
    </body>
    </html>
    """

# --- 2. GİRİŞ / KAYIT VE PROJE ÜRETME API'LERİ ---
@app.post("/api/auth")
async def auth_user(request: Request):
    body = await request.json()
    username = body.get("username")
    password = body.get("password")
    
    user = await users_db.find_one({"username": username})
    if not user:
        await users_db.insert_one({"username": username, "password": password})
        return {"status": "ok", "action": "registered"}
    else:
        if user.get("password") == password:
            return {"status": "ok", "action": "logged_in"}
        return {"status": "error", "message": "Hatalı şifre"}

@app.post("/api/create-project")
async def create_project_api():
    random_bytes = uuid.uuid4().bytes
    project_key = hashlib.md5(random_bytes).hexdigest()
    return {"status": "ok", "project_key": project_key}

# --- 3. HERKESE AÇIK (READ / WRITE / DELETE) REST API ---
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def handle_request(path: str, request: Request):
    method = request.method
    clean_path = path.strip("/")

    # A) Sonunda .json YOKSA -> Temizleme / Silme Alanı
    if not clean_path.endswith(".json"):
        if method == "DELETE":
            await collection.delete_many({"_key": {"$regex": f"^{clean_path}"}})
            return {"status": "cleared", "deleted_path": clean_path}
        return {
            "status": "cleanup_zone",
            "message": "Sonunda .json olmayan adresler temizleme alanidir."
        }

    # B) Sonunda .json VARSA -> Herkese Açık Read / Write Alanı
    db_key = clean_path[:-5]

    if method == "GET":
        doc = await collection.find_one({"_key": db_key}, {"_id": 0})
        if doc:
            return doc.get("value")
        return None

    elif method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            body = {}

        await collection.update_one(
            {"_key": db_key},
            {"$set": {"_key": db_key, "value": body}},
            upsert=True
        )
        return body

    elif method == "DELETE":
        await collection.delete_one({"_key": db_key})
        return {"status": "ok", "deleted": db_key}
