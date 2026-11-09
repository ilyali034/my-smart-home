import aiosqlite
from datetime import datetime, timezone
from typing import Any
from typing import Optional

class DeviceRepository:
    def __init__(self, db_path: str):
        self._connection: Optional[aiosqlite.Connection] = None
        self.db_path = db_path

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
            raise RuntimeError("DeviceRepository.connect() must be called first")
        return self._connection

    async def create_table(self) -> None:
        db = self._db()
        await db.execute(
            """CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                type TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                room TEXT,
                is_on INTEGER NOT NULL DEFAULT 0 CHECK (is_on IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        columns = await db.execute_fetchall("PRAGMA table_info(devices)")
        existing_columns = {column["name"] for column in columns}
        migrations = {
            "user_id": "ALTER TABLE devices ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE",
            "room": "ALTER TABLE devices ADD COLUMN room TEXT",
            "is_on": "ALTER TABLE devices ADD COLUMN is_on INTEGER NOT NULL DEFAULT 0",
            "created_at": "ALTER TABLE devices ADD COLUMN created_at TEXT NOT NULL DEFAULT ''",
            "updated_at": "ALTER TABLE devices ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        }
        for column, statement in migrations.items():
            if column not in existing_columns:
                await db.execute(statement)
        await db.execute("UPDATE devices SET created_at = CURRENT_TIMESTAMP WHERE created_at = ''")
        await db.execute("UPDATE devices SET updated_at = CURRENT_TIMESTAMP WHERE updated_at = ''")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id)")
        await db.commit()

    async def add_device(self, user_id: int, device_name: str, device_type: str, room: Optional[str]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        db = self._db()
        cursor = await db.execute(
            "INSERT INTO devices (user_id, device_name, type, room, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, device_name.strip(), device_type.strip(), room.strip() if room else None, now, now),
        )
        await db.commit()
        return await self.get_device(cursor.lastrowid, user_id)  # type: ignore[return-value]

    async def get_device(self, device_id: int, user_id: int) -> Optional[dict[str, Any]]:
        cursor = await self._db().execute(
            "SELECT * FROM devices WHERE id = ? AND user_id = ?", (device_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row is not None else None

    async def list_devices(
        self, user_id: int, room: Optional[str] = None, device_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        conditions = ["user_id = ?"]
        values: list[Any] = [user_id]
        if room is not None:
            conditions.append("room = ?")
            values.append(room)
        if device_type is not None:
            conditions.append("type = ?")
            values.append(device_type)
        cursor = await self._db().execute(
            f"SELECT * FROM devices WHERE {' AND '.join(conditions)} ORDER BY id", values
        )
        return [dict(row) for row in await cursor.fetchall()]

    async def update_device(self, device_id: int, user_id: int, changes: dict[str, Any]) -> Optional[dict[str, Any]]:
        allowed_fields = {"device_name", "type", "room", "is_on"}
        updates = {key: value for key, value in changes.items() if key in allowed_fields}
        if not updates:
            return await self.get_device(device_id, user_id)
        if "device_name" in updates:
            updates["device_name"] = updates["device_name"].strip()
        if "type" in updates:
            updates["type"] = updates["type"].strip()
        if "room" in updates and updates["room"] is not None:
            updates["room"] = updates["room"].strip()
        if "is_on" in updates:
            updates["is_on"] = int(updates["is_on"])
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        assignments = ", ".join(f"{field} = ?" for field in updates)
        values = [*updates.values(), device_id, user_id]
        cursor = await self._db().execute(
            f"UPDATE devices SET {assignments} WHERE id = ? AND user_id = ?", values
        )
        await self._db().commit()
        if cursor.rowcount == 0:
            return None
        return await self.get_device(device_id, user_id)

    async def delete_device(self, device_id: int, user_id: int) -> bool:
        cursor = await self._db().execute(
            "DELETE FROM devices WHERE id = ? AND user_id = ?", (device_id, user_id)
        )
        await self._db().commit()
        return cursor.rowcount > 0
