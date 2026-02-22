import sqlite3
import os
import logging
from typing import List
from config import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    # Ensure the directory exists if DB_PATH contains a directory
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Create a table to track processed papers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_papers (
            paper_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def is_paper_processed(paper_id: str) -> bool:
    """Checks if a paper has already been processed."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_papers WHERE paper_id = ?", (paper_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_paper_processed(paper_id: str, title: str):
    """Marks a paper as processed in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO processed_papers (paper_id, title) VALUES (?, ?)",
            (paper_id, title)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        logger.warning(f"Paper {paper_id} is already marked as processed.")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
