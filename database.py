import sqlite3


def create_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            city TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def save_user_data(user_id, latitude, longitude, city):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (user_id, latitude, longitude, city)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            latitude=excluded.latitude,
            longitude=excluded.longitude,
            city=excluded.city
    """,
        (user_id, latitude, longitude, city),
    )
    conn.commit()
    conn.close()


def get_user_city(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT city FROM users WHERE user_id = ?", (int(user_id),))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_user_coordinates(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT latitude, longitude FROM users WHERE user_id = ?", (int(user_id),)
    )

    result = cursor.fetchone()
    conn.close()
    return result if result else (None, None)
