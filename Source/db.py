import sqlite3, pathlib, datetime

db_path = pathlib.Path(__file__).parent / "data" / "tickets.db"
db_path.parent.mkdir(exist_ok=True)

def setup_ticket_db():
    schema ="""
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id TEXT PRIMARY KEY,
        status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
        client_uid TEXT NOT NULL,
        client_channel_id TEXT NOT NULL,
        client_parent_ts TEXT NOT NULL,
        admin_channel_id TEXT NOT NULL,
        admin_parent_ts TEXT NOT NULL,
        client_title TEXT NOT NULL,
        created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_client_thread ON tickets (client_channel_id, client_parent_ts);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_thread ON tickets (admin_channel_id, admin_parent_ts);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_status ON tickets (status);
    """

    with sqlite3.connect(db_path) as con:
        con.executescript(schema)
        print("tickets.db initialized at", db_path)

def connect_db():
    return sqlite3.connect(db_path)

def create_ticket(ticket_id, status, client_uid, client_channel_id, client_parent_ts, admin_channel_id, admin_parent_ts, client_title):
    with connect_db() as con:
        con.execute("""
        INSERT INTO tickets(
            ticket_id, status, client_uid, client_channel_id, client_parent_ts, admin_channel_id,
            admin_parent_ts, client_title, created_at
        ) VALUES (?, 'open', ?, ?, ?, ?, ?, ?, NULL, ?));
        """, (
            ticket_id, status, client_uid, client_channel_id, client_parent_ts, admin_channel_id,
            admin_parent_ts, client_title, datetime.datetime.utcnow().isoformat()
        ))

def find_client_ticket(channel_id, parent_ts):
    with connect_db() as con:
        cur = con.execute("""
        SELECT * FROM tickets
            WHERE client_channel_id = ? AND client_parent_ts = ?
        """, (channel_id, parent_ts))
        return cur.fetchone()

def close_ticket(ticket_id):
    with connect_db() as con:
        con.execute("""
        UPDATE tickets SET status = ? WHERE ticket_id = ?
        """, ('closed', ticket_id))