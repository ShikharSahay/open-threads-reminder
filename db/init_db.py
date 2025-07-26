import psycopg2
import psycopg2.extras
from psycopg2 import sql
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

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
    - AI analysis storage and user profile caching
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
        Create the specified database and tables if they don't already exist.
        
        Args:
            database: Name of the database to check/create
            channels: List of channel dictionaries with 'channel_name' and 'channel_id' keys
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

            # Create master tables first
            self._create_master_tables()

            # Create/update channel tables
            for channel in channels:
                table_name = channel["channel_name"].replace("-", "_")
                
                # Validate table name
                if not table_name.replace('_', '').isalnum():
                    raise ValueError(f"Table name contains invalid characters: {table_name}")
                
                self._create_or_update_channel_table(table_name)
                
                # Insert/update channel in master table
                self.upsert_channel_info(
                    channel_id=channel["channel_id"],
                    channel_name=channel["channel_name"], 
                    table_name=table_name
                )

        except psycopg2.Error as e:
            print(f"Error setting up database/table: {e}")
            raise
        except ValueError as e:
            print(f"Invalid name: {e}")
            raise

    def _create_master_tables(self):
        """Create the master channels and user_profiles tables."""
        
        # Create channels master table
        create_channels_query = """
            CREATE TABLE IF NOT EXISTS channels (
                channel_id VARCHAR(50) PRIMARY KEY,
                channel_name VARCHAR(100) NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                thread_count INTEGER DEFAULT 0,
                active_thread_count INTEGER DEFAULT 0,
                last_activity TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.cursor.execute(create_channels_query)
        print("Master channels table created/verified")

        # Create user profiles cache table
        create_profiles_query = """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100),
                display_name VARCHAR(100),
                real_name VARCHAR(100), 
                profile_image_url TEXT,
                profile_image_24 TEXT,
                profile_image_32 TEXT,
                profile_image_48 TEXT,
                profile_image_72 TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.cursor.execute(create_profiles_query)
        print("User profiles cache table created/verified")

    def _create_or_update_channel_table(self, table_name: str):
        """Create channel table with all enhanced columns from the beginning."""
        
        # Create complete table with all enhanced columns
        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                thread_ts TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                reply_count INTEGER DEFAULT 0,
                latest_reply TIMESTAMP,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_thread_name TEXT,
                ai_description TEXT, 
                ai_stakeholders TEXT DEFAULT '[]',  -- JSON array as string
                ai_priority VARCHAR(10),
                ai_confidence DECIMAL(3,2),
                github_issue TEXT,  -- "owner/repo#123"
                jira_ticket TEXT,   -- "PROJECT-123" 
                thread_issue TEXT,  -- "#456"
                ai_analysis_json TEXT,  -- Full AI response
                last_bot_message_ts TIMESTAMP,  -- When bot last sent message
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(thread_ts, channel_id)
            )
        """).format(sql.Identifier(table_name))
        
        self.cursor.execute(create_table_query)
        print(f"Enhanced channel table created: {table_name}")

    def store_thread_in_table(self, table: str, thread_data: Dict):
        """
        Insert or update a thread's data in the specified table with AI analysis.

        Args:
            table: Target table name
            thread_data: Dictionary with thread information including AI analysis
        """
        ts_latest_reply = thread_data['latest_reply']
        ts_float = float(ts_latest_reply)
        sql_timestamp = datetime.fromtimestamp(ts_float)

        ts_created_at = thread_data['thread_ts']
        ts_float = float(ts_created_at)
        sql_created_at = datetime.fromtimestamp(ts_float)

        # Prepare stakeholders as JSON string if it's a list
        ai_stakeholders = thread_data.get('ai_stakeholders', '[]')
        if isinstance(ai_stakeholders, list):
            ai_stakeholders = json.dumps(ai_stakeholders)

        query = sql.SQL("""
            INSERT INTO {} (
                thread_ts, channel_id, user_id, reply_count, latest_reply, status, created_at,
                ai_thread_name, ai_description, ai_stakeholders, ai_priority, ai_confidence,
                github_issue, jira_ticket, thread_issue, ai_analysis_json, last_bot_message_ts, updated_at
            )
            VALUES (
                %(thread_ts)s, %(channel_id)s, %(user_id)s, %(reply_count)s, %(latest_reply)s, 
                %(status)s, %(created_at)s, %(ai_thread_name)s, %(ai_description)s, 
                %(ai_stakeholders)s, %(ai_priority)s, %(ai_confidence)s, %(github_issue)s, 
                %(jira_ticket)s, %(thread_issue)s, %(ai_analysis_json)s, %(last_bot_message_ts)s, %(updated_at)s
            )
            ON CONFLICT (thread_ts, channel_id)
            DO UPDATE SET
                reply_count = EXCLUDED.reply_count,
                latest_reply = EXCLUDED.latest_reply,
                ai_thread_name = COALESCE(EXCLUDED.ai_thread_name, {}.ai_thread_name),
                ai_description = COALESCE(EXCLUDED.ai_description, {}.ai_description),
                ai_stakeholders = COALESCE(EXCLUDED.ai_stakeholders, {}.ai_stakeholders),
                ai_priority = COALESCE(EXCLUDED.ai_priority, {}.ai_priority),
                ai_confidence = COALESCE(EXCLUDED.ai_confidence, {}.ai_confidence),
                github_issue = COALESCE(EXCLUDED.github_issue, {}.github_issue),
                jira_ticket = COALESCE(EXCLUDED.jira_ticket, {}.jira_ticket),
                thread_issue = COALESCE(EXCLUDED.thread_issue, {}.thread_issue),
                ai_analysis_json = COALESCE(EXCLUDED.ai_analysis_json, {}.ai_analysis_json),
                last_bot_message_ts = COALESCE(EXCLUDED.last_bot_message_ts, {}.last_bot_message_ts),
                updated_at = EXCLUDED.updated_at
        """).format(sql.Identifier(table), sql.Identifier(table), sql.Identifier(table), 
                    sql.Identifier(table), sql.Identifier(table), sql.Identifier(table), 
                    sql.Identifier(table), sql.Identifier(table), sql.Identifier(table), 
                    sql.Identifier(table), sql.Identifier(table))

        # Prepare the dict for SQL
        thread_data_sql = {
            **thread_data,
            'latest_reply': sql_timestamp,
            'created_at': sql_created_at,
            'ai_stakeholders': ai_stakeholders,
            'ai_analysis_json': thread_data.get('ai_analysis_json'),
            'last_bot_message_ts': thread_data.get('last_bot_message_ts'),
            'updated_at': datetime.now()
        }

        try:
            self.cursor.execute(query, thread_data_sql)
        except psycopg2.Error as e:
            print(f"Error inserting data: {e}")
            raise

    def upsert_channel_info(self, channel_id: str, channel_name: str, table_name: str):
        """Insert or update channel information in the master channels table."""
        query = """
            INSERT INTO channels (channel_id, channel_name, table_name, last_activity)
            VALUES (%(channel_id)s, %(channel_name)s, %(table_name)s, %(last_activity)s)
            ON CONFLICT (channel_id) 
            DO UPDATE SET
                channel_name = EXCLUDED.channel_name,
                table_name = EXCLUDED.table_name,
                last_activity = EXCLUDED.last_activity
        """
        
        try:
            self.cursor.execute(query, {
                'channel_id': channel_id,
                'channel_name': channel_name, 
                'table_name': table_name,
                'last_activity': datetime.now()
            })
        except psycopg2.Error as e:
            print(f"Error upserting channel info: {e}")
            raise

    def store_user_profile(self, user_profile: Dict):
        """Store or update user profile information from Slack API."""
        query = """
            INSERT INTO user_profiles (
                user_id, name, display_name, real_name, profile_image_url,
                profile_image_24, profile_image_32, profile_image_48, profile_image_72, last_updated
            )
            VALUES (
                %(user_id)s, %(name)s, %(display_name)s, %(real_name)s, %(profile_image_url)s,
                %(profile_image_24)s, %(profile_image_32)s, %(profile_image_48)s, %(profile_image_72)s, %(last_updated)s
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                display_name = EXCLUDED.display_name,
                real_name = EXCLUDED.real_name,
                profile_image_url = EXCLUDED.profile_image_url,
                profile_image_24 = EXCLUDED.profile_image_24,
                profile_image_32 = EXCLUDED.profile_image_32,
                profile_image_48 = EXCLUDED.profile_image_48,
                profile_image_72 = EXCLUDED.profile_image_72,
                last_updated = EXCLUDED.last_updated
        """
        
        try:
            self.cursor.execute(query, {
                **user_profile,
                'last_updated': datetime.now()
            })
        except psycopg2.Error as e:
            print(f"Error storing user profile: {e}")
            raise

    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get cached user profile, returns None if not found or stale."""
        query = """
            SELECT * FROM user_profiles 
            WHERE user_id = %s 
            AND last_updated > NOW() - INTERVAL '24 hours'
        """
        
        try:
            self.cursor.execute(query, (user_id,))
            return self.cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Error fetching user profile: {e}")
            return None

    def get_all_channels(self) -> List[Dict]:
        """Get all channels from the master channels table."""
        query = """
            SELECT channel_id, channel_name, table_name, thread_count, 
                   active_thread_count, last_activity, created_at
            FROM channels 
            ORDER BY channel_name
        """
        
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error fetching channels: {e}")
            raise

    def update_channel_stats(self, channel_id: str):
        """Update thread counts for a channel."""
        # Get table name for this channel
        self.cursor.execute("SELECT table_name FROM channels WHERE channel_id = %s", (channel_id,))
        result = self.cursor.fetchone()
        if not result:
            return
            
        table_name = result['table_name']
        
        # Count total and active threads
        query = sql.SQL("""
            UPDATE channels SET 
                thread_count = (SELECT COUNT(*) FROM {}),
                active_thread_count = (SELECT COUNT(*) FROM {} WHERE status = 'open'),
                last_activity = (SELECT MAX(latest_reply) FROM {})
            WHERE channel_id = %s
        """).format(sql.Identifier(table_name), sql.Identifier(table_name), sql.Identifier(table_name))
        
        try:
            self.cursor.execute(query, (channel_id,))
        except psycopg2.Error as e:
            print(f"Error updating channel stats: {e}")
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

    def can_bot_send_message(self, table: str, thread_ts: str, channel_id: str, cooldown_minutes: int) -> bool:
        """Check if bot can send a message based on cooldown period."""
        query = sql.SQL("""
            SELECT last_bot_message_ts FROM {}
            WHERE thread_ts = %s AND channel_id = %s
        """).format(sql.Identifier(table))
        
        try:
            self.cursor.execute(query, (thread_ts, channel_id))
            result = self.cursor.fetchone()
            
            if not result or not result['last_bot_message_ts']:
                # No previous bot message, can send
                return True
            
            last_bot_message = result['last_bot_message_ts']
            cooldown_timedelta = timedelta(minutes=cooldown_minutes)
            
            # Check if enough time has passed since last bot message
            return datetime.now() - last_bot_message >= cooldown_timedelta
            
        except psycopg2.Error as e:
            print(f"Error checking bot message cooldown: {e}")
            # Default to allowing message on error
            return True

    def update_bot_message_timestamp(self, table: str, thread_ts: str, channel_id: str) -> bool:
        """Update the timestamp when bot sends a message to a thread."""
        query = sql.SQL("""
            UPDATE {} 
            SET last_bot_message_ts = %s, updated_at = %s
            WHERE thread_ts = %s AND channel_id = %s
        """).format(sql.Identifier(table))
        
        try:
            current_time = datetime.now()
            self.cursor.execute(query, (current_time, current_time, thread_ts, channel_id))
            return self.cursor.rowcount > 0
        except psycopg2.Error as e:
            print(f"Error updating bot message timestamp: {e}")
            return False
