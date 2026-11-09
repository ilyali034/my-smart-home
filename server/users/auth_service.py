import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Optional

import aiosqlite

from server.engine.database.user_repository import UserRepository


class AuthService:
	_PBKDF2_ITERATIONS = 310_000

	def __init__(self, user_repository: UserRepository, secret_key: str, token_ttl_minutes: int = 60):
		if not secret_key:
			raise ValueError("A non-empty token signing key is required")
		self.user_repository = user_repository
		self.secret_key = secret_key.encode("utf-8")
		self.token_ttl_minutes = token_ttl_minutes

	@classmethod
	def _hash_password(cls, password: str) -> str:
		salt = secrets.token_bytes(16)
		digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cls._PBKDF2_ITERATIONS)
		return "pbkdf2_sha256${}${}${}".format(
			cls._PBKDF2_ITERATIONS,
			base64.urlsafe_b64encode(salt).decode("ascii"),
			base64.urlsafe_b64encode(digest).decode("ascii"),
		)

	@classmethod
	def _verify_password(cls, password: str, encoded_hash: str) -> bool:
		try:
			algorithm, iterations, encoded_salt, encoded_digest = encoded_hash.split("$", 3)
			if algorithm != "pbkdf2_sha256":
				return False
			salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
			expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
			actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
			return hmac.compare_digest(actual, expected)
		except (ValueError, TypeError):
			return False

	async def register(self, email: str, password: str) -> dict[str, Any]:
		normalized_email = email.strip().lower()
		if await self.user_repository.get_by_email(normalized_email) is not None:
			raise ValueError("An account with this email already exists")
		try:
			return await self.user_repository.create_user(normalized_email, self._hash_password(password))
		except aiosqlite.IntegrityError as error:
			raise ValueError("An account with this email already exists") from error

	async def login(self, email: str, password: str) -> Optional[dict[str, Any]]:
		user = await self.user_repository.get_by_email(email)
		if user is None or not self._verify_password(password, user["password_hash"]):
			return None
		return user

	def create_access_token(self, user_id: int) -> str:
		now = int(time.time())
		payload = {"sub": user_id, "iat": now, "exp": now + self.token_ttl_minutes * 60}
		encoded_payload = base64.urlsafe_b64encode(
			json.dumps(payload, separators=(",", ":")).encode("utf-8")
		).rstrip(b"=").decode("ascii")
		signature = hmac.new(self.secret_key, encoded_payload.encode("ascii"), hashlib.sha256).digest()
		encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
		return f"{encoded_payload}.{encoded_signature}"

	def get_user_id_from_token(self, token: str) -> Optional[int]:
		try:
			encoded_payload, encoded_signature = token.split(".", 1)
			expected_signature = hmac.new(self.secret_key, encoded_payload.encode("ascii"), hashlib.sha256).digest()
			supplied_signature = base64.urlsafe_b64decode(
				encoded_signature + "=" * (-len(encoded_signature) % 4)
			)
			if not hmac.compare_digest(expected_signature, supplied_signature):
				return None
			payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
			payload = json.loads(payload_bytes)
			user_id = payload.get("sub")
			expires_at = payload.get("exp")
			if not isinstance(user_id, int) or not isinstance(expires_at, int) or expires_at <= int(time.time()):
				return None
			return user_id
		except (ValueError, TypeError, AttributeError, UnicodeDecodeError, json.JSONDecodeError):
			return None
