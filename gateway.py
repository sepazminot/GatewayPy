import os
import time
import httpx
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

# Configuración desde variables de entorno
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "https://localhost:3000")
PORT = int(os.getenv("PORT", "8000"))

# Cliente HTTP compartido para reutilizar conexiones
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10.0) as client:
        app.state.client = client
        yield

app = FastAPI(lifespan=lifespan)

# Health check con verificación de los servicios
@app.get("/health/verbose")
async def health_verbose():
    client = app.state.client
    user_status = "down"
    try:
        resp = await client.get(f"{USER_SERVICE_URL}/health")
        if resp.status_code == 200:
            user_status = "up"
    except Exception:
        pass
    return {"gateway": "up", "user_service": user_status, "proxy_to": USER_SERVICE_URL}

# Proxy universal para las rutas de usuarios
@app.api_route("/api/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_users(request: Request, path: str):
    client = app.state.client
    
    # 🔥 CORREGIDO: Si path está vacío, no agregar barra extra
    if path:
        target_url = f"{USER_SERVICE_URL}/users/{path}"
    else:
        target_url = f"{USER_SERVICE_URL}/users"  # Sin barra al final
    
    body = await request.body()
    
    resp = await client.request(
        method=request.method,
        url=target_url,
        content=body,
        headers={"Content-Type": "application/json"}
    )
    
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    
    # Devolver la misma respuesta
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

# Si se ejecuta directamente
if __name__ == "__main__":
    import uvicorn
    print(f"🚪 Gateway iniciado en http://0.0.0.0:{PORT}")
    print(f"   → Proxy a: {USER_SERVICE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
