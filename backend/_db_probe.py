import sqlite3


DB_PATH = r"c:\Users\Prince\StudentAttendanceTrackingSystem\backend\db.sqlite3"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    tables = [row[0] for row in cur.execute("select name from sqlite_master where type='table' order by name")]
    print("tables", tables)
    print(
        "admin_rows",
        cur.execute(
            "select id, username, user_type, is_staff, is_active, last_login from webapp_user where username='admin'"
        ).fetchall(),
    )
    print("user_count", cur.execute("select count(*) from webapp_user").fetchone()[0])

    conn.close()


if __name__ == "__main__":
    main()