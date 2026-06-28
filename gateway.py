import os
import time
import httpx
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:3000")
PORT = int(os.getenv("PORT", "8000"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optimización de conexiones estables para pruebas de carga masivas
    limits = httpx.Limits(max_keepalive_connections=100, max_connections=500)
    async with httpx.AsyncClient(timeout=15.0, limits=limits) as client:
        app.state.client = client
        yield

app = FastAPI(lifespan=lifespan)

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

@app.api_route("/api/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_users(request: Request, path: str):
    client = app.state.client
    
    # 1. Normalizar barra final para evitar problemas de enrutamiento (Trailing slash)
    clean_path = path if path else ""
    target_url = f"{USER_SERVICE_URL}/users/{clean_path}".rstrip("/")
    if path.endswith("/"):
        target_url += "/"

    # 2. Preservar Query Parameters (?page=1&limit=10, etc.)
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    
    # 3. Clonar headers entrantes (Excluyendo 'host' para no confundir al proxy de la nube)
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    
    body = await request.body()
    
    # Reenviar petición
    resp = await client.request(
        method=request.method,
        url=target_url,
        content=body,
        headers=headers
    )
    
    # 4. Clonar headers de salida devueltos por el microservicio
    response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in ["content-length", "content-encoding"]}
    
    return Response(
        content=resp.content, 
        status_code=resp.status_code, 
        headers=response_headers,
        media_type="application/json"
    )

# Si se ejecuta directamente
if __name__ == "__main__":
    import uvicorn
    print(f"🚪 Gateway iniciado en http://0.0.0.0:{PORT}")
    print(f"   → Proxy a: {USER_SERVICE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)