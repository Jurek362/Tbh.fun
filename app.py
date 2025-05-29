from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import sqlite3
import re

app = Flask(__name__)

# Konfiguracja CORS - TYLKO jedna linia!
CORS(app, origins=['https://jurek362.github.io', 'http://localhost:3000', 'http://127.0.0.1:5500'])

# Inicjalizacja bazy danych
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Tabela użytkowników
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            link TEXT NOT NULL
        )
    ''')
    
    # Tabela wiadomości
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    conn.commit()
    conn.close()

# Inicjalizuj bazę danych przy starcie
init_db()

@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")

@app.route('/')
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'version': '1.0'
    })

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/create-user', methods=['POST'])
def create_user():
    """Stwórz nowego użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        
        # Walidacja username
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username jest wymagany'
            }), 400
        
        if len(username) < 3:
            return jsonify({
                'success': False,
                'error': 'Username musi mieć przynajmniej 3 znaki'
            }), 400
        
        if len(username) > 20:
            return jsonify({
                'success': False,
                'error': 'Username nie może być dłuższy niż 20 znaków'
            }), 400
        
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź czy username już istnieje
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Ta nazwa użytkownika jest już zajęta'
            }), 400
        
        # Utwórz użytkownika
        user_id = str(int(datetime.now().timestamp() * 1000))
        created_at = datetime.now().isoformat()
        link = f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        
        cursor.execute('''
            INSERT INTO users (id, username, created_at, link)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, created_at, link))
        
        conn.commit()
        conn.close()
        
        print(f"Użytkownik utworzony: {username} (ID: {user_id})")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'user_id': user_id,
            'username': username,
            'link': link
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/<username>', methods=['GET'])
def get_user_by_username(username):
    """Pobierz użytkownika po username - NAPRAWIONE"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'id': user[0],
                'username': user[1],
                'created_at': user[2],
                'link': user[3]
            }
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user-by-id/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Pobierz użytkownika po ID - NOWY ENDPOINT"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'id': user[0],
                'username': user[1],
                'created_at': user[2],
                'link': user[3]
            }
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Wyślij wiadomość do użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        message = data.get('message', '').strip()
        
        if not username or not message:
            return jsonify({
                'success': False,
                'error': 'Username i wiadomość są wymagane'
            }), 400
        
        if len(message) > 500:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie może być dłuższa niż 500 znaków'
            }), 400
        
        # Sprawdź czy użytkownik istnieje
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Zapisz wiadomość
        message_id = str(int(datetime.now().timestamp() * 1000))
        created_at = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO messages (id, username, message, created_at)
            VALUES (?, ?, ?, ?)
        ''', (message_id, username, message, created_at))
        
        conn.commit()
        conn.close()
        
        print(f"Wiadomość wysłana do {username}")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość została wysłana pomyślnie!'
        })
        
    except Exception as e:
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/messages/<user_id>', methods=['GET'])
def get_messages(user_id):
    """Pobierz wiadomości użytkownika po user_id"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Najpierw znajdź username na podstawie user_id
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        username = user[0]
        
        # Pobierz wiadomości
        cursor.execute('''
            SELECT id, message, created_at 
            FROM messages 
            WHERE username = ? 
            ORDER BY created_at DESC
        ''', (username,))
        
        messages = cursor.fetchall()
        conn.close()
        
        messages_list = []
        for msg in messages:
            messages_list.append({
                'id': msg[0],
                'message': msg[1],
                'created_at': msg[2]
            })
        
        return jsonify({
            'success': True,
            'data': messages_list,
            'count': len(messages_list)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint nie istnieje'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'success': False,
        'error': 'Metoda nie dozwolona'
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Wewnętrzny błąd serwera'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("🚀 Uruchamianie serwera Flask...")
    print(f"📡 CORS włączony")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
        )
