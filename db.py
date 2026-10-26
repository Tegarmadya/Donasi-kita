"""
Database connection and execution utilities for DonasiKita.
Uses mysql-connector-python with parameterized queries and transaction support.
"""

import mysql.connector
from mysql.connector import Error, errorcode
from contextlib import contextmanager
import config


def get_server_connection():
    """Connects to MySQL server without specifying a database (for DB initialization)."""
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            autocommit=True,
            charset="utf8mb4"
        )
        return connection
    except Error as e:
        print(f"[ERROR] Failed to connect to MySQL server: {e}")
        raise e


def get_db_connection():
    """Connects to the DonasiKita database."""
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4"
        )
        return connection
    except Error as e:
        if e.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"[WARN] Database '{config.DB_NAME}' does not exist. Attempting creation...")
            create_database_if_not_exists()
            return mysql.connector.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                charset="utf8mb4"
            )
        else:
            print(f"[ERROR] Database connection failed: {e}")
            raise e


def create_database_if_not_exists():
    """Creates the target database if it does not already exist."""
    conn = get_server_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        cursor.close()
        print(f"[INFO] Database '{config.DB_NAME}' checked/created successfully.")
    finally:
        conn.close()


@contextmanager
def get_db_cursor(commit=False, dictionary=True):
    """Context manager for acquiring a database cursor with automatic cleanup."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor, conn
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def execute_query(sql, params=None, fetch_all=False, fetch_one=False, commit=False):
    """
    Executes a parameterized SQL query safely.
    
    Args:
        sql (str): SQL statement with %s placeholders.
        params (tuple or list): Parameters for the SQL statement.
        fetch_all (bool): If True, returns list of dictionary records.
        fetch_one (bool): If True, returns single dictionary record.
        commit (bool): If True, commits the transaction.
        
    Returns:
        Result data or last inserted id / affected rows count.
    """
    with get_db_cursor(commit=commit, dictionary=True) as (cursor, conn):
        cursor.execute(sql, params or ())
        
        if fetch_one:
            return cursor.fetchone()
        if fetch_all:
            return cursor.fetchall()
        if commit:
            return {
                "last_insert_id": cursor.lastrowid,
                "rowcount": cursor.rowcount
            }
        return None


def execute_script(sql_script_content):
    """
    Executes a multi-statement SQL script (e.g., schema.sql).
    Splits statements by semicolon while ignoring comments and delimiters.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Clean script
        statements = sql_script_content.split(";")
        for stmt in statements:
            clean_stmt = stmt.strip()
            if clean_stmt:
                cursor.execute(clean_stmt)
        conn.commit()
        cursor.close()
        print("[INFO] SQL script executed successfully.")
    finally:
        conn.close()


def test_connection():
    """Quick diagnostic utility to check database status."""
    try:
        create_database_if_not_exists()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION(), DATABASE();")
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        return {
            "status": "success",
            "version": res[0],
            "database": res[1],
            "message": "Connected to MySQL successfully."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    result = test_connection()
    print("Database Connection Test:", result)
