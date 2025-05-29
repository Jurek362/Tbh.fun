# app.py - Naprawiony Flask backend
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

# ===== KONFIGURACJA CORS =====
CORS(app, origins=['https://jurek362.github.io', 'http://localhost:3000', 'http://127.0.0.1:5500'])

# Tymczasowa baza danych w pamięci (w produkcji użyj prawdziwej bazy danych)
users_db = {}
messages_db = {}

@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== ROUTES =====

@app.route('/')
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'cors_enabled': True,
        'timestamp': datetime.now().isoformat()
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
    """Create new user"""
    try:
        # Pobierz dane JSON
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip().lower()
        
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
        
        # Sprawdź czy username zawiera tylko dozwolone znaki
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź czy username już istnieje
        if username in users_db:
            return jsonify({
                'success': False,
                'error': 'Ta nazwa użytkownika jest już zajęta'
            }), 400
        
        # Utwórz użytkownika
        user_id = str(int(datetime.now().timestamp() * 1000))
        user_data = {
            'id': user_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'message_count': 0
        }
        
        # Zapisz do "bazy danych"
        users_db[username] = user_data
        messages_db[username] = []
        
        print(f"Użytkownik utworzony: {username} (ID: {user_id})")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'username': username,
            'user_id': user_id,
            'link': f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/user/<username>', methods=['GET'])
def get_user(username):
    """Sprawdź czy użytkownik istnieje"""
    try:
        username = username.lower().strip()
        
        if username in users_db:
            return jsonify({
                'success': True,
                'exists': True,
                'username': username
            })
        else:
            return jsonify({
                'success': False,
                'exists': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
    except Exception as e:
        print(f"Błąd podczas sprawdzania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Wyślij anonimową wiadomość"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip().lower()
        message = data.get('message', '').strip()
        
        if not username or not message:
            return jsonify({
                'success': False,
                'error': 'Username i wiadomość są wymagane'
            }), 400
        
        if len(message) > 500:
            return jsonify({
                'success': False,
                'error': 'Wiadomość jest za długa (max 500 znaków)'
            }), 400
        
        # Sprawdź czy użytkownik istnieje
        if username not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Dodaj wiadomość
        message_data = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        messages_db[username].append(message_data)
        users_db[username]['message_count'] += 1
        
        print(f"Wysłano wiadomość do {username}")
        
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

@app.route('/api/messages/<username>', methods=['GET'])
def get_messages(username):
    """Pobierz wiadomości użytkownika"""
    try:
        username = username.lower().strip()
        
        if username not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(username, [])
        
        return jsonify({
            'success': True,
            'messages': user_messages,
            'count': len(user_messages)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Pobierz wszystkich użytkowników (do testów)"""
    try:
        users_list = list(users_db.values())
        
        return jsonify({
            'success': True,
            'users': users_list,
            'count': len(users_list)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkowników: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint nie istnieje',
        'path': request.path
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'success': False,
        'error': 'Metoda nie dozwolona',
        'method': request.method,
        'path': request.path
    }), 405

@app.errorhandler(500)
def internal_error(error):
    print(f"Błąd serwera: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Wewnętrzny błąd serwera'
    }), 500

# ===== MAIN =====
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
