"""Servidor exclusivamente para prueba de navegador en loopback."""
import uvicorn
from app.auth import hash_password
from app.main import create_app

if __name__ == "__main__":
    app = create_app({"cliente-prueba": hash_password("solo-prueba-local-2026")},
                     ".local/browser-traces.jsonl", secure_cookie=False)
    uvicorn.run(app, host="127.0.0.1", port=8765, access_log=False)
