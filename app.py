from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import os
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
import sys # Import sys for exiting on critical error

app = Flask(__name__)
CORS(app)

# --- Konfiguracja bazy danych PostgreSQL ---
DB_NAME = os.environ.get('DB_NAME', 'your_db_name')
DB_USER = os.environ.get('DB_USER', 'your_db_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'your_db_password')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')

def get_db_connection():
    """Ustanawia i zwraca połączenie z bazą danych."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5 # Dodano timeout połączenia
        )
        return conn
    except Exception as e:
        print(f"BŁĄD KRYTYCZNY: Nie udało się nawiązać połączenia z bazą danych: {e}", file=sys.stderr)
        return None

def init_db():
    """Tworzy tabele w bazie danych, jeśli nie istnieją."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
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
            print("Tabele bazy danych zostały zainicjowane lub już istniały.")
        except Exception as e:
            conn.rollback()
            print(f"BŁĄD: Podczas inicjalizacji tabel bazy danych wystąpił błąd: {e}", file=sys.stderr)
            raise # Ponownie rzuć wyjątek, aby sygnalizować problem
        finally:
            conn.close()
    else:
        print("BŁĄD: Nie można zainicjować bazy danych: brak połączenia.", file=sys.stderr)
        raise ConnectionError("Nie można nawiązać połączenia z bazą danych podczas inicjalizacji.")

# Wywołaj inicjalizację bazy danych przy starcie aplikacji
try:
    with app.app_context():
        init_db()
except (ConnectionError, Exception) as e:
    print(f"KRYTYCZNY BŁĄD STARTOWY: Aplikacja nie może połączyć się z bazą danych lub zainicjować tabel. {e}", file=sys.stderr)
    # W środowisku produkcyjnym można by tutaj podjąć decyzje o wyłączeniu aplikacji
    # lub przejściu w tryb konserwacji. Na Render.com to po prostu pojawi się w logach.

# --- Funkcje do interakcji z bazą danych ---

def _get_profile_by_user_id(user_id):
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Brak połączenia z bazą danych.")
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql.SQL("SELECT user_id, username FROM users WHERE user_id = %s"), (user_id,))
            profile = cur.fetchone()
            return dict(profile) if profile else None
    except Exception as e:
        print(f"BŁĄD DB: Nie udało się pobrać profilu po ID '{user_id}': {e}", file=sys.stderr)
        raise RuntimeError(f"Błąd bazy danych podczas pobierania profilu: {e}")
    finally:
        conn.close()

def _get_profile_by_username(username):
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Brak połączenia z bazą danych.")
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql.SQL("SELECT user_id, username FROM users WHERE username = %s"), (username,))
            profile = cur.fetchone()
            return dict(profile) if profile else None
    except Exception as e:
        print(f"BŁĄD DB: Nie udało się pobrać profilu po nazwie użytkownika '{username}': {e}", file=sys.stderr)
        raise RuntimeError(f"Błąd bazy danych podczas pobierania profilu po nazwie: {e}")
    finally:
        conn.close()

def _save_profile(user_id, username):
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Brak połączenia z bazą danych.") # Rzuć konkretny błąd
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql.SQL("SELECT user_id, username FROM users WHERE user_id = %s"), (user_id,))
            existing_profile = cur.fetchone()

            if existing_profile:
                cur.execute(sql.SQL("UPDATE users SET username = %s WHERE user_id = %s RETURNING user_id, username"),
                            (username, user_id))
            else:
                cur.execute(sql.SQL("INSERT INTO users (user_id, username) VALUES (%s, %s) RETURNING user_id, username"),
                            (user_id, username))
            
            profile = cur.fetchone()
            conn.commit()
            return dict(profile) if profile else None
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        print(f"Nazwa użytkownika '{username}' jest już zajęta.", file=sys.stderr)
        raise ValueError("Nazwa użytkownika jest już zajęta.") # Rzuć konkretny błąd
    except Exception as e:
        conn.rollback()
        print(f"BŁĄD DB: Błąd zapisywania profilu w bazie danych: {e}", file=sys.stderr)
        raise RuntimeError(f"Błąd bazy danych podczas zapisywania profilu: {e}") # Rzuć ogólny błąd DB
    finally:
        conn.close()

def _add_question(recipient_user_id, text):
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Brak połączenia z bazą danych.")
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
        print(f"BŁĄD DB: Błąd dodawania pytania: {e}", file=sys.stderr)
        raise RuntimeError(f"Błąd bazy danych podczas dodawania pytania: {e}")
    finally:
        conn.close()

def _get_questions_for_user(user_id):
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Brak połączenia z bazą danych.")
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql.SQL("""
                SELECT id, recipient_user_id, text, timestamp, is_answered, answer_text, answer_timestamp
                FROM questions
                WHERE recipient_user_id = %s
                ORDER BY timestamp DESC
            """), (user_id,))
            questions = cur.fetchall()
            for q in questions:
                if q['timestamp']:
                    q['timestamp'] = q['timestamp'].isoformat()
                if q['answer_timestamp']:
                    q['answer_timestamp'] = q['answer_timestamp'].isoformat()
            return [dict(q) for q in questions]
    except Exception as e:
        print(f"BŁĄD DB: Błąd pobierania pytań dla użytkownika '{user_id}': {e}", file=sys.stderr)
        raise RuntimeError(f"Błąd bazy danych podczas pobierania pytań: {e}")
    finally:
        conn.close()

def _update_question_answer(question_id, answer_text):
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Brak połączenia z bazą danych.")
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
        print(f"BŁĄD DB: Błąd aktualizacji odpowiedzi na pytanie '{question_id}': {e}", file=sys.stderr)
        raise RuntimeError(f"Błąd bazy danych podczas aktualizacji odpowiedzi: {e}")
    finally:
        conn.close()

# --- Endpointy API ---

@app.route('/')
def home():
    return "Anonymous questions backend is running!"

@app.route('/api/profile', methods=['POST'])
def create_or_update_profile():
    data = request.get_json()
    user_id = data.get('userId')
    username = data.get('username')

    if not user_id or not username:
        return jsonify({'message': 'Brak userId lub username'}), 400

    try:
        profile = _save_profile(user_id, username)
        return jsonify(profile), 200
    except ValueError as e: # Obsługuje błąd "Nazwa użytkownika jest już zajęta."
        return jsonify({'message': str(e)}), 409
    except ConnectionError as e: # Obsługuje problemy z połączeniem do bazy danych
        print(f"BŁĄD API: Błąd połączenia z bazą danych w /api/profile: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd połączenia z bazą danych. Spróbuj ponownie później.'}), 500
    except RuntimeError as e: # Obsługuje ogólne błędy operacji na bazie danych
        print(f"BŁĄD API: Błąd operacji na bazie danych w /api/profile: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd serwera podczas zapisywania profilu. Spróbuj ponownie.'}), 500
    except Exception as e: # Obsługuje wszelkie inne nieoczekiwane błędy
        print(f"BŁĄD API: Nieoczekiwany błąd w /api/profile: {e}", file=sys.stderr)
        return jsonify({'message': 'Wystąpił nieoczekiwany błąd serwera.'}), 500

@app.route('/api/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        profile = _get_profile_by_user_id(user_id)
        if profile:
            return jsonify(profile), 200
        return jsonify({'message': 'Profil nie znaleziony.'}), 404
    except ConnectionError as e:
        print(f"BŁĄD API: Błąd połączenia z bazą danych w /api/profile/<user_id>: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd połączenia z bazą danych. Spróbuj ponownie później.'}), 500
    except RuntimeError as e:
        print(f"BŁĄD API: Błąd operacji na bazie danych w /api/profile/<user_id>: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd serwera podczas pobierania profilu. Spróbuj ponownie.'}), 500
    except Exception as e:
        print(f"BŁĄD API: Nieoczekiwany błąd w /api/profile/<user_id>: {e}", file=sys.stderr)
        return jsonify({'message': 'Wystąpił nieoczekiwany błąd serwera.'}), 500

@app.route('/api/questions', methods=['POST'])
def send_question():
    data = request.get_json()
    recipient_username = data.get('recipientUsername')
    text = data.get('text')

    if not recipient_username or not text:
        return jsonify({'message': 'Brak nazwy odbiorcy lub tekstu pytania.'}), 400

    try:
        recipient_profile = _get_profile_by_username(recipient_username)
        if not recipient_profile:
            return jsonify({'message': 'Odbiorca nie znaleziony.'}), 404

        question = _add_question(recipient_profile['user_id'], text)
        if question:
            return jsonify(question), 201
        return jsonify({'message': 'Nie udało się wysłać pytania.'}), 500
    except ConnectionError as e:
        print(f"BŁĄD API: Błąd połączenia z bazą danych w /api/questions: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd połączenia z bazą danych. Spróbuj ponownie później.'}), 500
    except RuntimeError as e:
        print(f"BŁĄD API: Błąd operacji na bazie danych w /api/questions: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd serwera podczas wysyłania pytania. Spróbuj ponownie.'}), 500
    except Exception as e:
        print(f"BŁĄD API: Nieoczekiwany błąd w /api/questions: {e}", file=sys.stderr)
        return jsonify({'message': 'Wystąpił nieoczekiwany błąd serwera.'}), 500

@app.route('/api/users/<user_id>/questions', methods=['GET'])
def get_user_questions(user_id):
    try:
        questions = _get_questions_for_user(user_id)
        return jsonify(questions), 200
    except ConnectionError as e:
        print(f"BŁĄD API: Błąd połączenia z bazą danych w /api/users/<user_id>/questions: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd połączenia z bazą danych. Spróbuj ponownie później.'}), 500
    except RuntimeError as e:
        print(f"BŁĄD API: Błąd operacji na bazie danych w /api/users/<user_id>/questions: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd serwera podczas pobierania pytań. Spróbuj ponownie.'}), 500
    except Exception as e:
        print(f"BŁĄD API: Nieoczekiwany błąd w /api/users/<user_id>/questions: {e}", file=sys.stderr)
        return jsonify({'message': 'Wystąpił nieoczekiwany błąd serwera.'}), 500

@app.route('/api/questions/<question_id>/answer', methods=['POST'])
def answer_question(question_id):
    data = request.get_json()
    user_id = data.get('userId')
    answer_text = data.get('answerText')

    if not user_id or not answer_text:
        return jsonify({'message': 'Brak userId lub tekstu odpowiedzi.'}), 400

    conn = None # Inicjalizuj conn poza try, aby było dostępne w finally
    try:
        conn = get_db_connection()
        if not conn:
            raise ConnectionError("Brak połączenia z bazą danych.")

        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql.SQL("SELECT recipient_user_id, is_answered FROM questions WHERE id = %s"), (question_id,))
            question_info = cur.fetchone()

        if not question_info:
            return jsonify({'message': 'Pytanie nie znalezione.'}), 404
        if question_info['recipient_user_id'] != user_id:
            return jsonify({'message': 'Nieautoryzowane działanie.'}), 403
        if question_info['is_answered']:
            return jsonify({'message': 'Pytanie już zostało odpowiedzione.'}), 400

        updated_question = _update_question_answer(question_id, answer_text)
        if updated_question:
            return jsonify(updated_question), 200
        return jsonify({'message': 'Nie udało się zaktualizować odpowiedzi.'}), 500
    except ConnectionError as e:
        print(f"BŁĄD API: Błąd połączenia z bazą danych w /api/questions/<question_id>/answer: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd połączenia z bazą danych. Spróbuj ponownie później.'}), 500
    except RuntimeError as e:
        print(f"BŁĄD API: Błąd operacji na bazie danych w /api/questions/<question_id>/answer: {e}", file=sys.stderr)
        return jsonify({'message': 'Błąd serwera podczas odpowiadania na pytanie. Spróbuj ponownie.'}), 500
    except Exception as e:
        print(f"BŁĄD API: Nieoczekiwany błąd w /api/questions/<question_id>/answer: {e}", file=sys.stderr)
        return jsonify({'message': 'Wystąpił nieoczekiwany błąd serwera.'}), 500
    finally:
        if conn: # Upewnij się, że połączenie jest zamknięte, jeśli zostało otwarte
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

