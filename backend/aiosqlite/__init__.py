"""
aiosqlite — Genuine async SQLite driver using standard library sqlite3 + asyncio.to_thread.
Fully compatible with SQLAlchemy 2.0 sqlite+aiosqlite dialect.
"""
from __future__ import annotations

import asyncio
import sqlite3
import threading
from typing import Any, Optional, Sequence


class Cursor:
    def __init__(self, raw_cur: sqlite3.Cursor):
        self._cur = raw_cur

    async def execute(self, sql: str, parameters: Sequence[Any] = ()) -> Cursor:
        await asyncio.to_thread(self._cur.execute, sql, parameters)
        return self

    async def executemany(self, sql: str, parameters: Sequence[Sequence[Any]]) -> Cursor:
        await asyncio.to_thread(self._cur.executemany, sql, parameters)
        return self

    async def close(self) -> None:
        await asyncio.to_thread(self._cur.close)

    async def fetchone(self) -> Any:
        return await asyncio.to_thread(self._cur.fetchone)

    async def fetchall(self) -> list[Any]:
        return await asyncio.to_thread(self._cur.fetchall)

    async def fetchmany(self, size: Optional[int] = None) -> list[Any]:
        if size is None:
            return await asyncio.to_thread(self._cur.fetchmany)
        return await asyncio.to_thread(self._cur.fetchmany, size)

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    @property
    def lastrowid(self) -> Optional[int]:
        return self._cur.lastrowid

    @property
    def description(self) -> Any:
        return self._cur.description

    def __aiter__(self):
        return self

    async def __anext__(self):
        row = await self.fetchone()
        if row is None:
            raise StopAsyncIteration
        return row


class Connection:
    def __init__(self, *args: Any, **kwargs: Any):
        self._args = args
        self._kwargs = kwargs
        self._conn: Optional[sqlite3.Connection] = None
        # Thread placeholder required by SQLAlchemy dialect check: connection._thread.daemon = True
        self._thread = threading.Thread(target=lambda: None)
        self.daemon = True

    def __await__(self):
        async def _async_connect():
            kw = dict(self._kwargs)
            kw["check_same_thread"] = False
            self._conn = await asyncio.to_thread(sqlite3.connect, *self._args, **kw)
            return self

        return _async_connect().__await__()

    async def cursor(self) -> Cursor:
        if self._conn is None:
            raise sqlite3.OperationalError("Database is not connected")
        cur = await asyncio.to_thread(self._conn.cursor)
        return Cursor(cur)

    async def commit(self) -> None:
        if self._conn is not None:
            await asyncio.to_thread(self._conn.commit)

    async def rollback(self) -> None:
        if self._conn is not None:
            await asyncio.to_thread(self._conn.rollback)

    async def close(self) -> None:
        if self._conn is not None:
            await asyncio.to_thread(self._conn.close)
            self._conn = None

    async def execute(self, sql: str, parameters: Sequence[Any] = ()) -> Cursor:
        cur = await self.cursor()
        await cur.execute(sql, parameters)
        return cur

    async def executemany(self, sql: str, parameters: Sequence[Sequence[Any]]) -> Cursor:
        cur = await self.cursor()
        await cur.executemany(sql, parameters)
        return cur

    async def create_function(self, *args: Any, **kwargs: Any) -> None:
        if self._conn is not None:
            await asyncio.to_thread(self._conn.create_function, *args, **kwargs)

    @property
    def isolation_level(self) -> Optional[str]:
        return self._conn.isolation_level if self._conn else None

    @isolation_level.setter
    def isolation_level(self, val: Optional[str]) -> None:
        if self._conn is not None:
            self._conn.isolation_level = val

    @property
    def row_factory(self) -> Any:
        return self._conn.row_factory if self._conn else None

    @row_factory.setter
    def row_factory(self, val: Any) -> None:
        if self._conn is not None:
            self._conn.row_factory = val


def connect(*args: Any, **kwargs: Any) -> Connection:
    return Connection(*args, **kwargs)


# DB-API 2.0 exception and version exports
DatabaseError = sqlite3.DatabaseError
Error = sqlite3.Error
IntegrityError = sqlite3.IntegrityError
NotSupportedError = sqlite3.NotSupportedError
OperationalError = sqlite3.OperationalError
ProgrammingError = sqlite3.ProgrammingError
sqlite_version = sqlite3.sqlite_version
sqlite_version_info = sqlite3.sqlite_version_info
