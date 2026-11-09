from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes.auth import router as auth_router
from server.api.routes.devices import router as devices_router
from server.engine.config import settings
from server.engine.database.device_repository import DeviceRepository
from server.engine.database.user_repository import UserRepository
from server.users.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
	settings.prepare_database_directory()
	users = UserRepository(settings.database_path)
	devices = DeviceRepository(settings.database_path)
	await users.connect()
	await devices.connect()
	await users.create_table()
	await devices.create_table()
	app.state.user_repository = users
	app.state.device_repository = devices
	app.state.auth_service = AuthService(
		users,
		settings.secret_key,
		token_ttl_minutes=settings.access_token_ttl_minutes,
	)
	try:
		yield
	finally:
		await devices.close()
		await users.close()


app = FastAPI(
	title="My Smart Home API",
	version="1.0.0",
	description="Authentication and device management API for a smart home.",
	lifespan=lifespan,
)
app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.cors_origins or [],
	allow_credentials=True,
	allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
	allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(devices_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}
