import psycopg2
import psycopg2.extras
from psycopg2 import sql
from datetime import datetime
from typing import Dict, List, Optional

class DBClient:
    """
    PostgreSQL database client for managing Slack thread data.
    
    This class provides a high-level interface for storing and retrieving
    Slack thread information across different channels. Each channel gets
    its own table for better data organization and performance.
    
    Features:
    - Automatic database and table creation
    - Safe SQL queries with injection protection
    - Thread lifecycle management (open/closed status)
    - Context manager support for automatic cleanup
    """
    
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

    def create_prerequisites(self, database: str, channels: List[Dict]):
        """
        Create the specified database and table if they don't already exist.
        
        Args:
            database: Name of the database to check/create
            channels: List of channel dictionaries with 'channel_name' key
        """
        try:
            # Check if database exists
            self.cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            if not self.cursor.fetchone():
                # Note: Database names cannot be parameterized in psycopg2
                # Ensure database name is safe before using it
                if not database.replace('_', '').replace('-', '').isalnum():
                    raise ValueError("Database name contains invalid characters")
                self.cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
                print(f"Database created: {database}")

            # Reconnect using the new database
            self.db_config["dbname"] = database
            self._connect()

            # Create the table if not exists
            for channel in channels:
                table_name = channel["channel_name"].replace("-", "_")
                
                # Validate table name
                if not table_name.replace('_', '').isalnum():
                    raise ValueError(f"Table name contains invalid characters: {table_name}")
                
                create_table_query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        thread_ts TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        reply_count INTEGER DEFAULT 0,
                        latest_reply TIMESTAMP,
                        status TEXT DEFAULT 'open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY(thread_ts, channel_id)
                    )
                """).format(sql.Identifier(table_name))
                
                self.cursor.execute(create_table_query)
                print(f"Table created: {table_name}")

        except psycopg2.Error as e:
            print(f"Error setting up database/table: {e}")
            raise
        except ValueError as e:
            print(f"Invalid name: {e}")
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

        ts_created_at = thread_data['thread_ts']
        ts_float = float(ts_created_at)
        sql_created_at = datetime.fromtimestamp(ts_float)

        query = sql.SQL("""
            INSERT INTO {} (
                thread_ts, channel_id, user_id, reply_count, latest_reply, status, created_at
            )
            VALUES (
                %(thread_ts)s, %(channel_id)s, %(user_id)s, %(reply_count)s,
                %(latest_reply)s, %(status)s, %(created_at)s
            )
            ON CONFLICT (thread_ts, channel_id)
            DO UPDATE SET
                reply_count = EXCLUDED.reply_count,
                latest_reply = EXCLUDED.latest_reply
        """).format(sql.Identifier(table))

        # Prepare the dict for SQL (replace Slack ts string with datetime object)
        thread_data_sql = {
            **thread_data,
            'latest_reply': sql_timestamp,
            'created_at': sql_created_at
        }

        try:
            self.cursor.execute(query, thread_data_sql)
        except psycopg2.Error as e:
            print(f"Error inserting data: {e}")
            raise

    def get_open_threads_within_range(self, table: str, days: int) -> List[Dict]:
        # Use psycopg2.sql for safe table name formatting
        query = sql.SQL("""
            SELECT * FROM {}
            WHERE status = 'open'
              AND created_at >= NOW() - INTERVAL %s
        """).format(sql.Identifier(table))
        
        self.cursor.execute(query, (f'{days} days',))
        return self.cursor.fetchall()

    def get_thread_by_id(self, table: str, thread_ts: str, channel_id: str) -> Optional[Dict]:
        """Get a specific thread by its timestamp and channel ID."""
        query = sql.SQL("""
            SELECT * FROM {}
            WHERE thread_ts = %s AND channel_id = %s
        """).format(sql.Identifier(table))
        
        try:
            self.cursor.execute(query, (thread_ts, channel_id))
            return self.cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Error fetching thread: {e}")
            raise

    def get_threads_by_status(self, table: str, status: str) -> List[Dict]:
        """Get all threads with a specific status."""
        query = sql.SQL("""
            SELECT * FROM {}
            WHERE status = %s
            ORDER BY created_at DESC
        """).format(sql.Identifier(table))
        
        try:
            self.cursor.execute(query, (status,))
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error fetching threads by status: {e}")
            raise

    def update_thread_reply_count(self, table: str, thread_id: str, channel_id: str, reply_count: int, last_reply) -> bool:
        """Update reply count and latest reply timestamp for a thread."""
        query = sql.SQL("""
            UPDATE {} 
            SET reply_count = %s, latest_reply = %s 
            WHERE thread_ts = %s AND channel_id = %s
        """).format(sql.Identifier(table))
        
        try:
            self.cursor.execute(query, (
                reply_count, last_reply, thread_id, channel_id
            ))
            return True
        except psycopg2.Error as e:
            print(f"Error updating thread reply count: {e}")
            raise

    def update_thread_as_closed(self, table: str, thread_id: str, channel_id: str) -> None:
        """Mark a thread as closed."""
        query = sql.SQL("""
            UPDATE {}
            SET status = 'closed'
            WHERE thread_ts = %s AND channel_id = %s
        """).format(sql.Identifier(table))
        
        try:
            self.cursor.execute(query, (thread_id, channel_id))
        except psycopg2.Error as e:
            print(f"Error closing thread: {e}")
            raise

    def delete_thread(self, table: str, thread_ts: str, channel_id: str) -> bool:
        """Delete a specific thread."""
        query = sql.SQL("""
            DELETE FROM {}
            WHERE thread_ts = %s AND channel_id = %s
        """).format(sql.Identifier(table))
        
        try:
            self.cursor.execute(query, (thread_ts, channel_id))
            return self.cursor.rowcount > 0
        except psycopg2.Error as e:
            print(f"Error deleting thread: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the current database."""
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            return self.cursor.fetchone()['exists']
        except psycopg2.Error as e:
            print(f"Error checking table existence: {e}")
            raise

    def close(self) -> None:
        """Close the connection and cursor safely."""
        try:
            if self.cursor and not self.cursor.closed:
                self.cursor.close()
                self.cursor = None
            if self.conn and not self.conn.closed:
                self.conn.close()
                self.conn = None
            print("Database connection closed.")
        except psycopg2.Error as e:
            print(f"Error closing connection: {e}")
        except Exception as e:
            print(f"Unexpected error closing connection: {e}")

    def __enter__(self):
        """Enable context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatically close connection when exiting context."""
        self.close()
