from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import os
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor # Aby wyniki zapytań były słownikami

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication from a different domain

# --- PostgreSQL Database Configuration ---
# IMPORTANT: Use environment variables for database credentials in production!
# On Render.com, set these variables in the "Environment" section for your Web Service.
DB_NAME = os.environ.get('DB_NAME', 'your_db_name')
DB_USER = os.environ.get('DB_USER', 'your_db_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'your_db_password')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

def init_db():
    """Creates database tables if they do not exist."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Table for user profiles
                cur.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                # Table for questions
                cur.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS questions (
                        id VARCHAR(255) PRIMARY KEY,
                        recipient_user_id VARCHAR(255) NOT NULL,
                        text TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_answered BOOLEAN DEFAULT FALSE,
                        answer_text TEXT,
                        answer_timestamp TIMESTAMP,
                        FOREIGN KEY (recipient_user_id) REFERENCES users(user_id)
                    );
                """))
            conn.commit()
            print("Database tables initialized or already existed.")
        except Exception as e:
            conn.rollback()
            print(f"Error during database table initialization: {e}")
        finally:
            conn.close()
    else:
        print("Cannot initialize database: no connection.")

# Call database initialization on application startup
with app.app_context():
    init_db()

# --- Functions for database interaction ---

def _get_profile_by_user_id(user_id):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql.SQL("SELECT user_id, username FROM users WHERE user_id = %s"), (user_id,))
                profile = cur.fetchone()
                return dict(profile) if profile else None
        except Exception as e:
            print(f"Error fetching profile by ID: {e}")
            return None
        finally:
            conn.close()
    return None

def _get_profile_by_username(username):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql.SQL("SELECT user_id, username FROM users WHERE username = %s"), (username,))
                profile = cur.fetchone()
                return dict(profile) if profile else None
        except Exception as e:
            print(f"Error fetching profile by username: {e}")
            return None
        finally:
            conn.close()
    return None

def _save_profile(user_id, username):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Check if profile already exists
                cur.execute(sql.SQL("SELECT user_id, username FROM users WHERE user_id = %s"), (user_id,))
                existing_profile = cur.fetchone()

                if existing_profile:
                    # Update existing profile
                    cur.execute(sql.SQL("UPDATE users SET username = %s WHERE user_id = %s RETURNING user_id, username"),
                                (username, user_id))
                else:
                    # Insert new profile
                    cur.execute(sql.SQL("INSERT INTO users (user_id, username) VALUES (%s, %s) RETURNING user_id, username"),
                                (user_id, username))
                
                profile = cur.fetchone()
                conn.commit()
                return dict(profile) if profile else None
        except psycopg2.errors.UniqueViolation:
            conn.rollback() # Rollback transaction in case of unique violation
            print(f"Username '{username}' is already taken.")
            raise ValueError("Username is already taken.")
        except Exception as e:
            conn.rollback()
            print(f"Error saving profile: {e}")
            return None
        finally:
            conn.close()
    return None

def _add_question(recipient_user_id, text):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                question_id = str(uuid.uuid4())
                cur.execute(sql.SQL("""
                    INSERT INTO questions (id, recipient_user_id, text)
                    VALUES (%s, %s, %s) RETURNING *
                """), (question_id, recipient_user_id, text))
                question = cur.fetchone()
                conn.commit()
                return dict(question) if question else None
        except Exception as e:
            conn.rollback()
            print(f"Error adding question: {e}")
            return None
        finally:
            conn.close()
    return None

def _get_questions_for_user(user_id):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql.SQL("""
                    SELECT id, recipient_user_id, text, timestamp, is_answered, answer_text, answer_timestamp
                    FROM questions
                    WHERE recipient_user_id = %s
                    ORDER BY timestamp DESC
                """), (user_id,))
                questions = cur.fetchall()
                # Convert dates to ISO format for JSON
                for q in questions:
                    if q['timestamp']:
                        q['timestamp'] = q['timestamp'].isoformat()
                    if q['answer_timestamp']:
                        q['answer_timestamp'] = q['answer_timestamp'].isoformat()
                return [dict(q) for q in questions]
        except Exception as e:
            print(f"Error fetching questions for user: {e}")
            return []
        finally:
            conn.close()
    return []

def _update_question_answer(question_id, answer_text):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql.SQL("""
                    UPDATE questions
                    SET answer_text = %s, is_answered = TRUE, answer_timestamp = CURRENT_TIMESTAMP
                    WHERE id = %s AND is_answered = FALSE
                    RETURNING *
                """), (answer_text, question_id))
                updated_question = cur.fetchone()
                conn.commit()
                if updated_question:
                    updated_question = dict(updated_question)
                    if updated_question['timestamp']:
                        updated_question['timestamp'] = updated_question['timestamp'].isoformat()
                    if updated_question['answer_timestamp']:
                        updated_question['answer_timestamp'] = updated_question['answer_timestamp'].isoformat()
                    return updated_question
                return None
        except Exception as e:
            conn.rollback()
            print(f"Error updating question answer: {e}")
            return None
        finally:
            conn.close()
    return None

# --- API Endpoints (logic unchanged, only DB function calls) ---

@app.route('/')
def home():
    return "Anonymous questions backend is running!"

@app.route('/api/profile', methods=['POST'])
def create_or_update_profile():
    data = request.get_json()
    user_id = data.get('userId')
    username = data.get('username')

    if not user_id or not username:
        return jsonify({'message': 'Missing userId or username'}), 400

    try:
        profile = _save_profile(user_id, username)
        if profile:
            return jsonify(profile), 200
        else:
            return jsonify({'message': 'Failed to save profile.'}), 500
    except ValueError as e: # Handle unique username error
        return jsonify({'message': str(e)}), 409
    except Exception as e:
        print(f"Error in /api/profile endpoint: {e}")
        return jsonify({'message': 'An internal server error occurred.'}), 500

@app.route('/api/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    profile = _get_profile_by_user_id(user_id)
    if profile:
        return jsonify(profile), 200
    return jsonify({'message': 'Profile not found.'}), 404

@app.route('/api/questions', methods=['POST'])
def send_question():
    data = request.get_json()
    recipient_username = data.get('recipientUsername')
    text = data.get('text')

    if not recipient_username or not text:
        return jsonify({'message': 'Missing recipient username or question text.'}), 400

    recipient_profile = _get_profile_by_username(recipient_username)
    if not recipient_profile:
        return jsonify({'message': 'Recipient not found.'}), 404

    question = _add_question(recipient_profile['user_id'], text)
    if question:
        return jsonify(question), 201
    return jsonify({'message': 'Failed to send question.'}), 500

@app.route('/api/users/<user_id>/questions', methods=['GET'])
def get_user_questions(user_id):
    questions = _get_questions_for_user(user_id)
    return jsonify(questions), 200

@app.route('/api/questions/<question_id>/answer', methods=['POST'])
def answer_question(question_id):
    data = request.get_json()
    user_id = data.get('userId')
    answer_text = data.get('answerText')

    if not user_id or not answer_text:
        return jsonify({'message': 'Missing userId or answer text.'}), 400

    # First, check if the question exists and if userId is its recipient
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database connection error.'}), 500
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql.SQL("SELECT recipient_user_id, is_answered FROM questions WHERE id = %s"), (question_id,))
            question_info = cur.fetchone()

        if not question_info:
            return jsonify({'message': 'Question not found.'}), 404
        if question_info['recipient_user_id'] != user_id:
            return jsonify({'message': 'Unauthorized action.'}), 403
        if question_info['is_answered']:
            return jsonify({'message': 'Question has already been answered.'}), 400

        updated_question = _update_question_answer(question_id, answer_text)
        if updated_question:
            return jsonify(updated_question), 200
        return jsonify({'message': 'Failed to update answer.'}), 500
    except Exception as e:
        print(f"Error in /api/questions/<question_id>/answer endpoint: {e}")
        return jsonify({'message': 'An internal server error occurred.'}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # In a production environment (Render.com), Gunicorn will run the application.
    # This is only for local testing.
    # Make sure you have a local PostgreSQL server running.
    app.run(debug=True, host='0.0.0.0', port=5000)

