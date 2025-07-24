import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Dict

class DBClient:
    def __init__(self, db_config: Dict):
        """
        Initialize the database client with connection settings.
        
        Args:
            db_config: Dictionary with keys: host, port, user, password, (optional) dbname
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self._connect()

    def _connect(self):
        """Connect to the database using current config."""
        self.close()  # Close existing connection if any
        self.conn = psycopg2.connect(**self.db_config)
        self.conn.autocommit = True
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def create_prerequisites(self, database: str, channels: list[Dict]):
        """
        Create the specified database and table if they don't already exist.
        
        Args:
            database: Name of the database to check/create
            table: Name of the table to check/create
        """
        try:
            # Check if database exists
            self.cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            if not self.cursor.fetchone():
                self.cursor.execute(f"CREATE DATABASE {database}")
                print(f"Database created: {database}")

            # Reconnect using the new database
            self.db_config["dbname"] = database
            self._connect()

            # Create the table if not exists
            for channel in channels:
                table = channel["channel_name"]
                table = table.replace("-", "_")
                self.cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        thread_ts TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        reply_count INTEGER DEFAULT 0,
                        latest_reply TIMESTAMP,
                        PRIMARY KEY(thread_ts, channel_id)
                    )
                """)
                print(f"Table created: {table}")

        except psycopg2.Error as e:
            print(f"Error setting up database/table: {e}")
            raise

    def store_thread_in_table(self, table: str, thread_data: Dict):
        """
        Insert or update a thread's data in the specified table.

        Args:
            table: Target table name
            thread_data: Dictionary with keys -
                    thread_ts, channel_id, user_id, reply_count, latest_reply, status
                        latest_reply should be Slack 'ts' string (e.g., "1753346981.244749")
        """
        ts_latest_reply = thread_data['latest_reply']
        ts_float = float(ts_latest_reply)
        sql_timestamp = datetime.fromtimestamp(ts_float)

        query = f"""
            INSERT INTO {table} (thread_ts, channel_id, user_id, reply_count, latest_reply, status)
            VALUES (
                %(thread_ts)s, %(channel_id)s, %(user_id)s,
                %(reply_count)s, %(latest_reply)s, %(status)s
            )
            ON CONFLICT (thread_ts, channel_id)
            DO UPDATE SET
                reply_count = EXCLUDED.reply_count,
                latest_reply = EXCLUDED.latest_reply
        """

        # Prepare the dict for SQL (replace Slack ts string with datetime object)
        thread_data_sql = {
            **thread_data,
            'latest_reply': sql_timestamp
        }

        try:
            self.cursor.execute(query, thread_data_sql)
        except psycopg2.Error as e:
            print(f"Error inserting data: {e}")
            raise

    def get_open_threads_within_range(self, table: str, days: int):
        query = """
        SELECT * FROM %s
        WHERE status = 'open'
          AND created_at >= NOW() - INTERVAL %s;
        """
        self.cursor.execute(query, (table ,f'{days} days',))
        return self.cursor.fetchall()

    def update_thread_reply_count(self, thread_id, channel_id, reply_count, last_reply):
        query = """
            UPDATE threads 
            SET reply_count = %s, last_reply_ts = %s 
            WHERE threads_ts = %s AND channel_id = %s;
        """
        self.cursor.execute(query, (
            reply_count, last_reply, thread_id, channel_id
        ))
        return True

    def update_thread_as_closed(self, thread_id, channel_id):
        query = """
            UPDATE threads
            SET status = 'closed'
            WHERE thread_ts = %s AND channel_id = %s;
        """
        self.cursor.execute(
            query, (
                thread_id, channel_id
            )
        )

    def close(self):
        """Close the connection and cursor safely."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("Database connection closed.")
        except psycopg2.Error as e:
            print(f"Error closing connection: {e}")

    def __enter__(self):
        """Enable context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatically close connection when exiting context."""
        self.close()
