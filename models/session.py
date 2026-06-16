import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from services.database import execute_command, execute_command_with_return, execute_query, execute_query_one


def _row(record) -> dict:
    return {k: record[k] for k in record.keys()}

# SELECT clause shared by list and single-fetch queries
_SELECT = """
    SELECT s.session_id, s.user_id, s.activity_id, s.device_id, s.device_name,
           s.start_time, s.end_time, s.duration_seconds, s.duration_hms, s.created_at,
           u.user_name, a.activity_name
    FROM activity_sessions s
    JOIN users u ON s.user_id = u.user_id
    JOIN activity a ON s.activity_id = a.activity_id
"""


def _build_filters(
    search: Optional[str],
    activity_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[str, list]:
    conditions: list[str] = []
    params: list = []
    idx = 1

    if search:
        # Partial, case-insensitive search across BOTH user name and activity name.
        conditions.append(f"(LOWER(u.user_name) LIKE ${idx} OR LOWER(a.activity_name) LIKE ${idx})")
        params.append(f"%{search.strip().lower()}%")
        idx += 1
    if activity_id:
        conditions.append(f"s.activity_id = ${idx}")
        params.append(uuid.UUID(activity_id))
        idx += 1
    if start_date:
        conditions.append(f"s.start_time >= ${idx}")
        params.append(datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        idx += 1
    if end_date:
        end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        conditions.append(f"s.start_time < ${idx}")
        params.append(end_dt)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def _build_export_filters(
    user_id: Optional[str],
    activity_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[str, list]:
    conditions: list[str] = []
    params: list = []
    idx = 1

    if user_id:
        conditions.append(f"s.user_id = ${idx}")
        params.append(uuid.UUID(user_id))
        idx += 1
    if activity_id:
        conditions.append(f"s.activity_id = ${idx}")
        params.append(uuid.UUID(activity_id))
        idx += 1
    if start_date:
        conditions.append(f"s.start_time >= ${idx}")
        params.append(datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        idx += 1
    if end_date:
        end_dt = datetime.combine(end_date, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        conditions.append(f"s.start_time < ${idx}")
        params.append(end_dt)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


class ActivitySession:
    def __init__(self, **kwargs):
        self.session_id: str = str(kwargs.get("session_id", ""))
        self.user_id: str = str(kwargs.get("user_id", ""))
        self.activity_id: str = str(kwargs.get("activity_id", ""))
        self.device_id: str = kwargs.get("device_id", "")
        self.device_name: str = kwargs.get("device_name", "shoe")
        self.start_time: Optional[datetime] = kwargs.get("start_time")
        self.end_time: Optional[datetime] = kwargs.get("end_time")
        self.duration_seconds: int = kwargs.get("duration_seconds", 0)
        self.duration_hms: str = kwargs.get("duration_hms", "00:00:00")
        self.created_at: Optional[datetime] = kwargs.get("created_at")
        # Populated via JOIN
        self.user_name: str = kwargs.get("user_name", "")
        self.activity_name: str = kwargs.get("activity_name", "")

    @classmethod
    async def find_by_id(cls, session_id: str) -> Optional["ActivitySession"]:
        query = _SELECT + " WHERE s.session_id = $1"
        row = await execute_query_one(query, uuid.UUID(session_id))
        if row is None:
            return None
        return cls(**_row(row))

    @classmethod
    async def create(
        cls,
        user_id: str,
        activity_id: str,
        device_id: str,
        device_name: str,
        start_time: datetime,
        end_time: datetime,
        duration_seconds: int,
    ) -> "ActivitySession":
        query = """
            INSERT INTO activity_sessions
                (session_id, user_id, activity_id, device_id, device_name,
                 start_time, end_time, duration_seconds, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING session_id, user_id, activity_id, device_id, device_name,
                      start_time, end_time, duration_seconds, duration_hms, created_at
        """
        row = await execute_command_with_return(
            query,
            uuid.uuid4(),
            uuid.UUID(user_id),
            uuid.UUID(activity_id),
            device_id,
            device_name,
            start_time,
            end_time,
            duration_seconds,
        )
        if row is None:
            raise RuntimeError("INSERT RETURNING returned None unexpectedly")
        return cls(**_row(row))

    @classmethod
    async def get_list(
        cls,
        limit: int,
        offset: int,
        search: Optional[str] = None,
        activity_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> tuple[list["ActivitySession"], int]:
        where, params = _build_filters(search, activity_id, start_date, end_date)
        next_idx = len(params) + 1

        base_from = f"""
            FROM activity_sessions s
            JOIN users u ON s.user_id = u.user_id
            JOIN activity a ON s.activity_id = a.activity_id
            {where}
        """

        count_row = await execute_query_one(f"SELECT COUNT(*) {base_from}", *params)
        total = int(count_row["count"]) if count_row else 0

        list_query = f"""
            SELECT s.session_id, s.user_id, s.activity_id, s.device_id, s.device_name,
                   s.start_time, s.end_time, s.duration_seconds, s.created_at,
                   u.user_name, a.activity_name
            {base_from}
            ORDER BY s.created_at DESC
            LIMIT ${next_idx} OFFSET ${next_idx + 1}
        """
        rows = await execute_query(list_query, *params, limit, offset)
        return [cls(**_row(r)) for r in rows], total

    @classmethod
    async def get_all_for_export(
        cls,
        user_id: Optional[str] = None,
        activity_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list["ActivitySession"]:
        where, params = _build_export_filters(user_id, activity_id, start_date, end_date)
        query = f"{_SELECT} {where} ORDER BY s.start_time ASC"
        rows = await execute_query(query, *params)
        return [cls(**_row(r)) for r in rows]

    async def delete(self) -> bool:
        await execute_command(
            "DELETE FROM activity_sessions WHERE session_id = $1",
            uuid.UUID(self.session_id),
        )
        return True

    @classmethod
    async def bulk_delete(cls, session_ids: list[str]) -> int:
        uuid_list = [uuid.UUID(sid) for sid in session_ids]
        result = await execute_command(
            "DELETE FROM activity_sessions WHERE session_id = ANY($1::uuid[])", uuid_list
        )
        return int(result.split()[-1])

    @classmethod
    async def delete_all(cls) -> int:
        result = await execute_command("DELETE FROM activity_sessions")
        return int(result.split()[-1])

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "activity": self.activity_name,
            "device": self.device_id,
            "device_name": self.device_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at,
        }
