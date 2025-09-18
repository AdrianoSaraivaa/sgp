"""Provides a minimal base class for interacting with SQLite.

The classes in this project map directly onto tables in the
``pneumark.db`` database.  Rather than relying on heavy ORM
dependencies such as SQLAlchemy, this base class exposes a few simple
operations using Python's built‑in ``sqlite3`` module.  Subclasses
should define ``__tablename__`` matching the table name in the
database and be declared as dataclasses with fields corresponding to
the table columns.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, fields
from typing import Any, ClassVar, Iterable, List, Optional, Type, TypeVar


T = TypeVar("T", bound="BaseModel")


class BaseModel:
    """Minimal base class for table mapping.

    Subclasses should define a ``__tablename__`` class variable
    matching the table name and use ``@dataclass`` to define the
    columns.  This base class provides convenience methods for
    fetching records from the database.  It is intentionally light
    weight and does not provide full ORM behaviour.
    """

    #: Override in subclasses to specify the table name.
    __tablename__: ClassVar[str]

    #: Path to the SQLite database file.  Defaults to three levels up
    #: from this file's directory, which should resolve to
    #: ``pneumark.db`` when running within the project tree.  You can
    #: customise this via the ``PNEUMARK_DB`` environment variable.
    __database_path__: ClassVar[str] = os.getenv(
        "PNEUMARK_DB",
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "pneumark.db")
        ),
    )

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        """Create a new SQLite connection using the configured path."""
        conn = sqlite3.connect(cls.__database_path__)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def all(cls: Type[T]) -> List[T]:
        """Return all records from the table as a list of instances."""
        with cls._get_connection() as conn:
            cur = conn.execute(f"SELECT * FROM {cls.__tablename__}")
            rows = cur.fetchall()
            return [cls._from_row(row) for row in rows]

    @classmethod
    def get_by_id(cls: Type[T], id_value: Any) -> Optional[T]:
        """Return a single record by its primary key or ``None`` if not found."""
        pk_field = cls._primary_key_field_name()
        with cls._get_connection() as conn:
            cur = conn.execute(
                f"SELECT * FROM {cls.__tablename__} WHERE {pk_field} = ?",
                (id_value,),
            )
            row = cur.fetchone()
            return cls._from_row(row) if row is not None else None

    @classmethod
    def _primary_key_field_name(cls) -> str:
        """Return the name of the first field, assumed to be the primary key."""
        # Assume the first dataclass field corresponds to the primary key
        return fields(cls)[0].name

    @classmethod
    def _from_row(cls: Type[T], row: sqlite3.Row) -> T:
        """Construct an instance from a SQLite ``Row`` object."""
        kwargs = {key: row[key] for key in row.keys()}
        return cls(**kwargs)  # type: ignore[arg-type]

    def save(self) -> None:
        """Insert or update this record in the database.

        If the primary key attribute is ``None`` then a new row will be
        inserted.  Otherwise, the existing row with the same primary
        key will be updated.  Note: only basic type conversion is
        supported and JSON columns are passed through as Python
        structures.
        """
        table = self.__class__.__tablename__
        pk_field = self.__class__._primary_key_field_name()
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        pk_value = data.pop(pk_field)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        values = list(data.values())
        with self.__class__._get_connection() as conn:
            cur = conn.cursor()
            if pk_value is None:
                # Insert new record
                cur.execute(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                    values,
                )
                setattr(self, pk_field, cur.lastrowid)
            else:
                # Update existing record
                assignments = ", ".join([f"{col} = ?" for col in data.keys()])
                cur.execute(
                    f"UPDATE {table} SET {assignments} WHERE {pk_field} = ?",
                    values + [pk_value],
                )
            conn.commit()

    def delete(self) -> None:
        """Delete this record from the database."""
        pk_field = self.__class__._primary_key_field_name()
        pk_value = getattr(self, pk_field)
        if pk_value is None:
            raise ValueError("Cannot delete an unsaved record (no primary key set)")
        with self.__class__._get_connection() as conn:
            conn.execute(
                f"DELETE FROM {self.__class__.__tablename__} WHERE {pk_field} = ?",
                (pk_value,),
            )
            conn.commit()