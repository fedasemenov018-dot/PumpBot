#!/usr/bin/env python3
"""Database initialization and management"""

import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.getenv('DATABASE_PATH', 'fitness_bot.db')


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with required tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        goal TEXT,
        level TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create workouts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        exercise TEXT NOT NULL,
        weight REAL,
        reps INTEGER,
        sets INTEGER,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Create achievements table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        exercise TEXT NOT NULL,
        max_weight REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        UNIQUE(user_id, exercise)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def user_exists(user_id):
    """Check if user exists"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def create_user(user_id, username, full_name, goal, level):
    """Create new user"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO users (user_id, username, full_name, goal, level)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, full_name, goal, level))
        conn.commit()
        logger.info(f"User {user_id} created successfully")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"User {user_id} already exists")
        return False
    finally:
        conn.close()


def log_workout(user_id, exercise, weight, reps, sets):
    """Log a workout"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO workouts (user_id, exercise, weight, reps, sets)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, exercise, weight, reps, sets))
    
    # Update achievements if this is a new max weight
    cursor.execute('''
    SELECT max_weight FROM achievements 
    WHERE user_id = ? AND exercise = ?
    ''', (user_id, exercise))
    result = cursor.fetchone()
    
    if result is None:
        cursor.execute('''
        INSERT INTO achievements (user_id, exercise, max_weight)
        VALUES (?, ?, ?)
        ''', (user_id, exercise, weight))
    elif weight > result[0]:
        cursor.execute('''
        UPDATE achievements SET max_weight = ? 
        WHERE user_id = ? AND exercise = ?
        ''', (weight, user_id, exercise))
    
    conn.commit()
    conn.close()
    logger.info(f"Workout logged for user {user_id}: {exercise}")


def get_week_stats(user_id):
    """Get workout statistics for the week"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT exercise, COUNT(*) as count, SUM(sets) as total_sets, 
           SUM(reps) as total_reps, MAX(weight) as max_weight
    FROM workouts
    WHERE user_id = ? AND logged_at >= datetime('now', '-7 days')
    GROUP BY exercise
    ORDER BY max_weight DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results


def get_achievements(user_id):
    """Get user achievements"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT exercise, max_weight FROM achievements
    WHERE user_id = ?
    ORDER BY max_weight DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results


def get_user_info(user_id):
    """Get user information"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result
