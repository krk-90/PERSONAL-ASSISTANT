from fastapi import FastAPI

from app.routes.auth import router as auth_router

fastapi_app = FastAPI(title="Personal Assistant API")
fastapi_app.include_router(auth_router)