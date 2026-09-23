import asyncio

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.routes.RAG import router as rag_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.services.chat_services import warm_start_cache

fastapi_app = FastAPI(title="Personal Assistant API")


def custom_openapi():
	if fastapi_app.openapi_schema:
		return fastapi_app.openapi_schema

	schema = get_openapi(
		title=fastapi_app.title,
		version="1.0.0",
		routes=fastapi_app.routes,
	)
	upload_schema = schema.get("components", {}).get("schemas", {}).get(
		"Body_upload_documents_rag_upload_post"
	)
	if upload_schema:
		upload_schema["properties"]["files"]["items"]["format"] = "binary"

	fastapi_app.openapi_schema = schema
	return schema


fastapi_app.openapi = custom_openapi


@fastapi_app.on_event("startup")
async def startup_event() -> None:
	def warm_cache_in_worker() -> None:
		asyncio.run(warm_start_cache())

	asyncio.create_task(asyncio.to_thread(warm_cache_in_worker))


fastapi_app.include_router(auth_router)
fastapi_app.include_router(health_router)
fastapi_app.include_router(rag_router)
fastapi_app.include_router(chat_router)
