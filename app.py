# app.py - Naprawiony Flask backend z poprawnym obsługiwaniem username
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)

# ===== KONFIGURACJA CORS =====
CORS(app, origins=['https://jurek362.github.io'])

# Tymczasowa baza danych w pamięci (w produkcji użyj prawdziwej bazy)
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
        'cors_enabled': True
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
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        
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
        
        # Sprawdź czy username nie jest już zajęty
        for user_id, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
                return jsonify({
                    'success': False,
                    'error': 'Ta nazwa użytkownika jest już zajęta'
                }), 400
        
        # Sprawdź dozwolone znaki
        import re
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Utwórz użytkownika
        user_id = str(int(datetime.now().timestamp() * 1000))
        user_data = {
            'id': user_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
        }
        
        # Zapisz do bazy
        users_db[user_id] = user_data
        messages_db[user_id] = []  # Pusta lista wiadomości
        
        # Zwróć link do wysyłania wiadomości (z username, nie ID)
        send_link = f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        
        print(f"Użytkownik utworzony: {user_id}, username: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'user_id': user_id,
            'username': username,
            'link': send_link
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/user/<username>', methods=['GET'])
def get_user_by_username(username):
    """Sprawdź czy użytkownik o danej nazwie istnieje"""
    try:
        # Szukaj użytkownika po username
        for user_id, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
                return jsonify({
                    'success': True,
                    'exists': True,
                    'data': {
                        'id': user_data['id'],
                        'username': user_data['username'],
                        'created_at': user_data['created_at']
                    }
                })
        
        # Użytkownik nie został znaleziony
        return jsonify({
            'success': False,
            'exists': False,
            'error': 'Użytkownik nie istnieje'
        }), 404
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
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
        
        username = data.get('username', '').strip()
        message = data.get('message', '').strip()
        
        if not username or not message:
            return jsonify({
                'success': False,
                'error': 'Username i wiadomość są wymagane'
            }), 400
        
        # Znajdź użytkownika po username
        target_user_id = None
        for user_id, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
                target_user_id = user_id
                break
        
        if not target_user_id:
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
        
        if target_user_id not in messages_db:
            messages_db[target_user_id] = []
        
        messages_db[target_user_id].append(message_data)
        
        print(f"Wiadomość wysłana do {username} (ID: {target_user_id})")
        
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
    """Pobierz wiadomości użytkownika"""
    try:
        if user_id not in messages_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        messages = messages_db.get(user_id, [])
        
        return jsonify({
            'success': True,
            'messages': messages,
            'count': len(messages)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Pobierz wszystkich użytkowników"""
    try:
        users = list(users_db.values())
        
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
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
    print(f"📡 CORS włączony dla: https://jurek362.github.io")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
          )
