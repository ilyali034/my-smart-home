import aiosqlite
from typing import Any, Optional


class UserRepository:
	def __init__(self, db_path: str):
		self.db_path = db_path
		self._connection: Optional[aiosqlite.Connection] = None

	async def connect(self) -> None:
		if self._connection is None:
			self._connection = await aiosqlite.connect(self.db_path)
			self._connection.row_factory = aiosqlite.Row
			await self._connection.execute("PRAGMA foreign_keys = ON")

	async def close(self) -> None:
		if self._connection is not None:
			await self._connection.close()
			self._connection = None

	def _db(self) -> aiosqlite.Connection:
		if self._connection is None:
			raise RuntimeError("UserRepository.connect() must be called first")
		return self._connection

	async def create_table(self) -> None:
		await self._db().execute(
			"""CREATE TABLE IF NOT EXISTS users (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				email TEXT NOT NULL COLLATE NOCASE UNIQUE,
				password_hash TEXT NOT NULL,
				created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
			)"""
		)
		await self._db().commit()

	async def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
		cursor = await self._db().execute(
			"INSERT INTO users (email, password_hash) VALUES (?, ?)", (email.strip().lower(), password_hash)
		)
		await self._db().commit()
		return await self.get_by_id(cursor.lastrowid)  # type: ignore[return-value]

	async def get_by_email(self, email: str) -> Optional[dict[str, Any]]:
		cursor = await self._db().execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
		row = await cursor.fetchone()
		return dict(row) if row is not None else None

	async def get_by_id(self, user_id: int) -> Optional[dict[str, Any]]:
		cursor = await self._db().execute("SELECT * FROM users WHERE id = ?", (user_id,))
		row = await cursor.fetchone()
		return dict(row) if row is not None else None
