from fastapi import FastAPI

from app.routes.RAG import router as rag_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router

fastapi_app = FastAPI(title="Personal Assistant API")
fastapi_app.include_router(auth_router)
fastapi_app.include_router(health_router)
fastapi_app.include_router(rag_router)
fastapi_app.include_router(chat_router)
