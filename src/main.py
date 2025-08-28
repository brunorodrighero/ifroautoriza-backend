# src/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
from datetime import datetime

from src.core.config import settings
from src.utils.logger import logger
from src.api.endpoints import auth, events, authorizations, users, campus # 1. IMPORTAR campus

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(title=settings.PROJECT_NAME)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORREÇÃO DO CORS AQUI ---
# Adiciona a origem do localhost de desenvolvimento à lista de origens permitidas
allowed_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
if "http://localhost:5173" not in allowed_origins:
    allowed_origins.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, # Usa a nova lista com o localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- FIM DA CORREÇÃO ---

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def log_requests_and_add_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f'{process_time:.2f}'
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    
    logger.info(f'"{request.method} {request.url.path}" {response.status_code} - {formatted_process_time}ms')
    return response

# Incluindo os routers na aplicação
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(events.router, prefix=f"{settings.API_V1_STR}/eventos", tags=["Events"])
app.include_router(authorizations.router, prefix=f"{settings.API_V1_STR}/autorizacoes", tags=["Authorizations"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/usuarios", tags=["Users"])
# 2. INCLUIR O NOVO ROTEADOR
app.include_router(campus.router, prefix=f"{settings.API_V1_STR}/campus", tags=["Campus"])


@app.get(f"{settings.API_V1_STR}/health", tags=["System"])
def health_check():
    return {"status": "OK", "timestamp": datetime.now()}