import sqlite3

class Database:
    def __init__(self, db_file):
        self.db_file = db_file
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_file)

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invocations (
                    request_id TEXT PRIMARY KEY,
                    timestamp DATETIME,
                    model_id TEXT,
                    identity_arn TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cache_read_tokens INTEGER,
                    cache_write_tokens INTEGER,
                    cost_usd REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON invocations (timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_identity_arn ON invocations (identity_arn)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model_id ON invocations (model_id)")
            conn.commit()

    def insert_invocation(self, invocation_data):
        with self._get_connection() as conn:
            cost = invocation_data.get('costUsd')
            
            conn.execute("""
                INSERT OR IGNORE INTO invocations (
                    request_id, timestamp, model_id, identity_arn, 
                    input_tokens, output_tokens, cache_read_tokens, 
                    cache_write_tokens, cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invocation_data['requestId'],
                invocation_data['timestamp'],
                invocation_data['modelId'],
                invocation_data['identityArn'],
                invocation_data.get('inputTokenCount', 0),
                invocation_data.get('outputTokenCount', 0),
                invocation_data.get('cacheReadInputTokenCount', 0),
                invocation_data.get('cacheWriteInputTokenCount', 0),
                cost
            ))
            conn.commit()

    def get_daily_summary(self, date_str):
        """
        Returns summary for a specific date (YYYY-MM-DD).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    model_id, 
                    COUNT(*) as count, 
                    SUM(input_tokens) as total_input, 
                    SUM(output_tokens) as total_output, 
                    SUM(cost_usd) as total_cost
                FROM invocations 
                WHERE date(timestamp) = ?
                GROUP BY model_id
            """, (date_str,))
            return cursor.fetchall()

    def get_user_summary(self, date_str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    identity_arn, 
                    SUM(cost_usd) as total_cost
                FROM invocations 
                WHERE date(timestamp) = ?
                GROUP BY identity_arn
                ORDER BY total_cost DESC
            """, (date_str,))
            return cursor.fetchall()

    def get_recent_invocations(self, limit=10):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, model_id, identity_arn, cost_usd
                FROM invocations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
