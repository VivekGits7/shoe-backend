import uuid
from typing import Optional

from services.database import execute_command, execute_command_with_return, execute_query, execute_query_one


def _row(record) -> dict:
    return {k: record[k] for k in record.keys()}


class Activity:
    def __init__(self, **kwargs):
        self.activity_id: str = str(kwargs.get("activity_id", ""))
        self.activity_name: str = kwargs.get("activity_name", "")
        self.created_at = kwargs.get("created_at")

    @classmethod
    async def find_by_id(cls, activity_id: str) -> Optional["Activity"]:
        row = await execute_query_one(
            "SELECT * FROM activity WHERE activity_id = $1", uuid.UUID(activity_id)
        )
        if row is None:
            return None
        return cls(**_row(row))

    @classmethod
    async def find_by_name(cls, activity_name: str) -> Optional["Activity"]:
        row = await execute_query_one(
            "SELECT * FROM activity WHERE LOWER(activity_name) = LOWER($1)", activity_name
        )
        if row is None:
            return None
        return cls(**_row(row))

    @classmethod
    async def create(cls, activity_name: str) -> "Activity":
        query = """
            INSERT INTO activity (activity_id, activity_name, created_at)
            VALUES ($1, $2, NOW())
            RETURNING *
        """
        row = await execute_command_with_return(query, uuid.uuid4(), activity_name)
        if row is None:
            raise RuntimeError("INSERT RETURNING returned None unexpectedly")
        return cls(**_row(row))

    @classmethod
    async def get_all(cls) -> list["Activity"]:
        rows = await execute_query("SELECT * FROM activity ORDER BY activity_name ASC")
        return [cls(**_row(r)) for r in rows]

    async def delete(self) -> bool:
        await execute_command(
            "DELETE FROM activity WHERE activity_id = $1",
            uuid.UUID(self.activity_id),
        )
        return True

    def to_dict(self) -> dict:
        return {
            "activity_id": self.activity_id,
            "activity_name": self.activity_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
