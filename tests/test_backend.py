import sqlite3
import tempfile
import unittest
from pathlib import Path

from server.engine.database.device_repository import DeviceRepository
from server.engine.database.user_repository import UserRepository
from server.users.auth_service import AuthService


class BackendRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.users = UserRepository(self.db_path)
        self.devices = DeviceRepository(self.db_path)
        await self.users.connect()
        await self.devices.connect()
        await self.users.create_table()
        await self.devices.create_table()
        self.auth = AuthService(self.users, "unit-test-secret", token_ttl_minutes=5)

    async def asyncTearDown(self) -> None:
        await self.devices.close()
        await self.users.close()
        self.temp_dir.cleanup()

    async def test_password_authentication_and_signed_tokens(self) -> None:
        user = await self.auth.register("Home@example.com", "safe-password-123")
        self.assertEqual(user["email"], "home@example.com")
        self.assertNotIn("safe-password-123", user["password_hash"])
        self.assertIsNotNone(await self.auth.login("HOME@example.com", "safe-password-123"))
        self.assertIsNone(await self.auth.login("home@example.com", "wrong-password"))
        with self.assertRaises(ValueError):
            await self.auth.register("home@example.com", "another-password")

        token = self.auth.create_access_token(user["id"])
        self.assertEqual(self.auth.get_user_id_from_token(token), user["id"])
        self.assertIsNone(self.auth.get_user_id_from_token(token + "tampered"))

    async def test_device_crud_is_scoped_to_owner(self) -> None:
        owner = await self.auth.register("owner@example.com", "owner-password-123")
        another_user = await self.auth.register("another@example.com", "another-password-123")
        device = await self.devices.add_device(owner["id"], "Kitchen light", "light", "Kitchen")

        self.assertEqual(device["is_on"], 0)
        self.assertEqual(len(await self.devices.list_devices(owner["id"], room="Kitchen")), 1)
        self.assertEqual(await self.devices.list_devices(another_user["id"]), [])
        self.assertIsNone(await self.devices.get_device(device["id"], another_user["id"]))

        updated = await self.devices.update_device(device["id"], owner["id"], {"is_on": True})
        self.assertIsNotNone(updated)
        self.assertEqual(updated["is_on"], 1)
        self.assertTrue(await self.devices.delete_device(device["id"], owner["id"]))
        self.assertFalse(await self.devices.delete_device(device["id"], owner["id"]))

    async def test_legacy_device_schema_is_migrated(self) -> None:
        legacy_path = str(Path(self.temp_dir.name) / "legacy.db")
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute(
                "CREATE TABLE devices (id INTEGER PRIMARY KEY AUTOINCREMENT, device_name TEXT NOT NULL, type TEXT NOT NULL)"
            )
            connection.execute("INSERT INTO devices (device_name, type) VALUES ('Old light', 'light')")
            connection.commit()
        finally:
            connection.close()

        legacy_users = UserRepository(legacy_path)
        legacy_devices = DeviceRepository(legacy_path)
        await legacy_users.connect()
        await legacy_devices.connect()
        await legacy_users.create_table()
        await legacy_devices.create_table()
        rows = await legacy_devices._db().execute_fetchall("SELECT * FROM devices")

        self.assertIsNone(rows[0]["user_id"])
        self.assertEqual(rows[0]["device_name"], "Old light")
        self.assertTrue(rows[0]["created_at"])
        await legacy_devices.close()
        await legacy_users.close()


if __name__ == "__main__":
    unittest.main()
