"""
SQLite database for storing thruster test results.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import ThrusterConfig, TestPoint, TestResult, DeadbandResult


class Database:
    """SQLite database for thruster test data."""

    def __init__(self, db_path: str = "thruster_tests.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating if necessary."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_tables(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Test results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thruster_type TEXT NOT NULL,
                thruster_id TEXT NOT NULL,
                min_pwm_us INTEGER NOT NULL,
                max_pwm_us INTEGER NOT NULL,
                neutral_pwm_us INTEGER NOT NULL,
                pwm_frequency_hz INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                notes TEXT,
                deadband_min_off INTEGER,
                deadband_max_off INTEGER,
                deadband_midpoint REAL,
                deadband_range INTEGER
            )
        ''')

        # Test points table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                pwm_us INTEGER NOT NULL,
                current_a REAL NOT NULL,
                voltage_v REAL NOT NULL,
                power_w REAL NOT NULL,
                thrust_kg REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES test_results (id)
            )
        ''')

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_test_points_test_id
            ON test_points (test_id)
        ''')

        conn.commit()

    def save_test_result(self, result: TestResult) -> int:
        """
        Save a complete test result to the database.

        Args:
            result: TestResult to save

        Returns:
            Database ID of saved test
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Insert test result
        cursor.execute('''
            INSERT INTO test_results (
                thruster_type, thruster_id, min_pwm_us, max_pwm_us,
                neutral_pwm_us, pwm_frequency_hz, start_time, end_time, notes,
                deadband_min_off, deadband_max_off, deadband_midpoint, deadband_range
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.config.thruster_type,
            result.config.thruster_id,
            result.config.min_pwm_us,
            result.config.max_pwm_us,
            result.config.neutral_pwm_us,
            result.config.pwm_frequency_hz,
            result.start_time.isoformat(),
            result.end_time.isoformat() if result.end_time else None,
            result.notes,
            result.deadband.min_off_pwm_us if result.deadband else None,
            result.deadband.max_off_pwm_us if result.deadband else None,
            result.deadband.midpoint_pwm_us if result.deadband else None,
            result.deadband.range_us if result.deadband else None
        ))

        test_id = cursor.lastrowid

        # Insert test points
        for point in result.test_points:
            cursor.execute('''
                INSERT INTO test_points (
                    test_id, pwm_us, current_a, voltage_v, power_w, thrust_kg, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_id,
                point.pwm_us,
                point.current_a,
                point.voltage_v,
                point.power_w,
                point.thrust_kg,
                point.timestamp.isoformat()
            ))

        conn.commit()
        return test_id

    def get_test_result(self, test_id: int) -> Optional[TestResult]:
        """
        Retrieve a test result by ID.

        Args:
            test_id: Database ID of test

        Returns:
            TestResult or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get test result
        cursor.execute('SELECT * FROM test_results WHERE id = ?', (test_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        # Get test points
        cursor.execute(
            'SELECT * FROM test_points WHERE test_id = ? ORDER BY pwm_us',
            (test_id,)
        )
        point_rows = cursor.fetchall()

        # Build objects
        config = ThrusterConfig(
            thruster_type=row['thruster_type'],
            thruster_id=row['thruster_id'],
            min_pwm_us=row['min_pwm_us'],
            max_pwm_us=row['max_pwm_us'],
            neutral_pwm_us=row['neutral_pwm_us'],
            pwm_frequency_hz=row['pwm_frequency_hz']
        )

        test_points = [
            TestPoint(
                pwm_us=p['pwm_us'],
                current_a=p['current_a'],
                voltage_v=p['voltage_v'],
                power_w=p['power_w'],
                thrust_kg=p['thrust_kg'],
                timestamp=datetime.fromisoformat(p['timestamp'])
            )
            for p in point_rows
        ]

        deadband = None
        if row['deadband_min_off'] is not None:
            deadband = DeadbandResult(
                min_off_pwm_us=row['deadband_min_off'],
                max_off_pwm_us=row['deadband_max_off'],
                midpoint_pwm_us=row['deadband_midpoint'],
                range_us=row['deadband_range']
            )

        return TestResult(
            test_id=test_id,
            config=config,
            test_points=test_points,
            deadband=deadband,
            start_time=datetime.fromisoformat(row['start_time']),
            end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
            notes=row['notes'] or ""
        )

    def get_all_tests(self) -> List[dict]:
        """
        Get summary of all tests.

        Returns:
            List of test summaries (id, thruster_type, thruster_id, start_time)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, thruster_type, thruster_id, start_time, end_time
            FROM test_results
            ORDER BY start_time DESC
        ''')

        return [
            {
                'id': row['id'],
                'thruster_type': row['thruster_type'],
                'thruster_id': row['thruster_id'],
                'start_time': row['start_time'],
                'end_time': row['end_time']
            }
            for row in cursor.fetchall()
        ]

    def delete_test(self, test_id: int):
        """
        Delete a test result and its points.

        Args:
            test_id: Database ID of test to delete
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM test_points WHERE test_id = ?', (test_id,))
        cursor.execute('DELETE FROM test_results WHERE id = ?', (test_id,))

        conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
