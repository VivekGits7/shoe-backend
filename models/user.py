import uuid
from typing import Optional

from services.database import execute_command, execute_command_with_return, execute_query, execute_query_one


def _row(record) -> dict:
    return {k: record[k] for k in record.keys()}


class User:
    def __init__(self, **kwargs):
        self.user_id: str = str(kwargs.get("user_id", ""))
        self.user_name: str = kwargs.get("user_name", "")
        self.device_name: Optional[str] = kwargs.get("device_name")
        self.device_id: str = kwargs.get("device_id", "")
        self.created_at = kwargs.get("created_at")

    @classmethod
    async def find_by_id(cls, user_id: str) -> Optional["User"]:
        row = await execute_query_one(
            "SELECT * FROM users WHERE user_id = $1", uuid.UUID(user_id)
        )
        if row is None:
            return None
        return cls(**_row(row))

    @classmethod
    async def find_by_name(cls, user_name: str) -> Optional["User"]:
        row = await execute_query_one(
            "SELECT * FROM users WHERE LOWER(user_name) = LOWER($1)", user_name
        )
        if row is None:
            return None
        return cls(**_row(row))

    @classmethod
    async def find_by_device_and_name(cls, device_id: str, user_name: str) -> Optional["User"]:
        row = await execute_query_one(
            "SELECT * FROM users WHERE device_id = $1 AND LOWER(user_name) = LOWER($2)",
            device_id,
            user_name,
        )
        if row is None:
            return None
        return cls(**_row(row))

    @classmethod
    async def create(cls, user_name: str, device_id: str, device_name: str) -> "User":
        query = """
            INSERT INTO users (user_id, user_name, device_id, device_name, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            RETURNING *
        """
        row = await execute_command_with_return(query, uuid.uuid4(), user_name, device_id, device_name)
        if row is None:
            raise RuntimeError("INSERT RETURNING returned None unexpectedly")
        return cls(**_row(row))

    @classmethod
    async def get_all(cls, search: Optional[str] = None) -> list["User"]:
        if search and search.strip():
            rows = await execute_query(
                "SELECT * FROM users WHERE user_name ILIKE $1 ORDER BY created_at DESC",
                f"%{search.strip()}%",
            )
        else:
            rows = await execute_query("SELECT * FROM users ORDER BY created_at DESC")
        return [cls(**_row(r)) for r in rows]

    async def delete(self) -> bool:
        user_uuid = uuid.UUID(self.user_id)
        # Cascade: remove the user's sessions first (FK), then the user itself.
        await execute_command("DELETE FROM activity_sessions WHERE user_id = $1", user_uuid)
        await execute_command("DELETE FROM users WHERE user_id = $1", user_uuid)
        return True

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
