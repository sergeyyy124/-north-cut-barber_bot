import sqlite3
from typing import Any


def get_connection(db_path: str) -> sqlite3.Connection:
    """Создаёт подключение к SQLite и настраивает доступ к колонкам по имени."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    """Создаёт таблицу bookings и уникальный индекс для защиты от двойной записи на один слот."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                client_name TEXT NOT NULL,
                service_id TEXT NOT NULL,
                service_title TEXT NOT NULL,
                price INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Не позволяем двум активным записям занять одинаковые дату и время
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_slot
            ON bookings (booking_date, booking_time)
            WHERE status = 'active'
            """
        )
        conn.commit()


def get_booked_times(db_path: str, booking_date: str) -> set[str]:
    """Возвращает множество занятых слотов времени на выбранную дату (формат YYYY-MM-DD)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT booking_time
            FROM bookings
            WHERE booking_date = ? AND status = 'active'
            """,
            (booking_date,),
        ).fetchall()
    return {row["booking_time"] for row in rows}


def create_booking(
    db_path: str,
    user_id: int,
    username: str | None,
    client_name: str,
    service_id: str,
    service_title: str,
    price: int,
    booking_date: str,
    booking_time: str,
) -> int | None:
    """
    Сохраняет новую запись в таблицу bookings и возвращает её ID.
    Если слот на эту дату и время уже занят, возвращает None.
    """
    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO bookings (
                    user_id, username, client_name,
                    service_id, service_title, price,
                    booking_date, booking_time, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
                """,
                (
                    user_id,
                    username,
                    client_name,
                    service_id,
                    service_title,
                    price,
                    booking_date,
                    booking_time,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        return None


def get_user_bookings(db_path: str, user_id: int) -> list[dict[str, Any]]:
    """Возвращает список активных записей конкретного пользователя."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, client_name, service_title, price, booking_date, booking_time
            FROM bookings
            WHERE user_id = ? AND status = 'active'
            ORDER BY booking_date ASC, booking_time ASC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def cancel_booking(db_path: str, booking_id: int, user_id: int) -> bool:
    """
    Отменяет активную запись по ID, проверяя принадлежность записи пользователю.
    Возвращает True, если запись успешно отменена.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE bookings
            SET status = 'cancelled'
            WHERE id = ? AND user_id = ? AND status = 'active'
            """,
            (booking_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
