# app.py - Naprawiony Flask backend z wszystkimi endpointami
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

# CORS Configuration
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

# ===== PODSTAWOWE ROUTES =====

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

# ===== USER MANAGEMENT =====

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
        
        # Sprawdź czy username zawiera tylko dozwolone znaki
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź czy username już istnieje
        for user_id, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
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
            'link': f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        }
        
        # Zapisz do bazy danych
        users_db[user_id] = user_data
        messages_db[user_id] = []  # Pusta lista wiadomości
        
        print(f"Użytkownik utworzony: {user_id} (@{username})")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'data': {
                'username': user_data['username'],
                'link': user_data['link'],
                'id': user_data['id']
            },
            # Dodaj user_id dla kompatybilności z frontendem
            'user_id': user_data['id']
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/user/<identifier>', methods=['GET'])
def get_user(identifier):
    """Pobierz użytkownika po ID lub username"""
    try:
        user_data = None
        
        # Sprawdź czy identifier to user_id
        if identifier in users_db:
            user_data = users_db[identifier]
        else:
            # Sprawdź czy identifier to username
            for user_id, data in users_db.items():
                if data['username'].lower() == identifier.lower():
                    user_data = data
                    break
        
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        return jsonify({
            'success': True,
            'data': user_data
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Pobierz wszystkich użytkowników"""
    try:
        users_list = list(users_db.values())
        
        return jsonify({
            'success': True,
            'data': users_list,
            'count': len(users_list)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkowników: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# ===== MESSAGE HANDLING =====

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
        
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username jest wymagany'
            }), 400
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie może być pusta'
            }), 400
        
        if len(message) > 500:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie może być dłuższa niż 500 znaków'
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
        
        # Utwórz wiadomość
        message_data = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        # Dodaj wiadomość do bazy danych
        if target_user_id not in messages_db:
            messages_db[target_user_id] = []
        
        messages_db[target_user_id].append(message_data)
        
        print(f"Wiadomość wysłana do @{username}: {message_data['id']}")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość została wysłana pomyślnie!'
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/messages/<user_id>', methods=['GET'])
def get_user_messages(user_id):
    """Pobierz wiadomości użytkownika"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(user_id, [])
        
        # Sortuj wiadomości od najnowszych
        user_messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': user_messages,
            'count': len(user_messages),
            'unread_count': len([msg for msg in user_messages if not msg['read']])
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/message/<message_id>/read', methods=['POST'])
def mark_message_read(message_id):
    """Oznacz wiadomość jako przeczytaną"""
    try:
        # Znajdź wiadomość we wszystkich użytkownikach
        for user_id, user_messages in messages_db.items():
            for message in user_messages:
                if message['id'] == message_id:
                    message['read'] = True
                    return jsonify({
                        'success': True,
                        'message': 'Wiadomość oznaczona jako przeczytana'
                    })
        
        return jsonify({
            'success': False,
            'error': 'Wiadomość nie istnieje'
        }), 404
        
    except Exception as e:
        print(f"Błąd podczas oznaczania wiadomości: {str(e)}")
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
    print("\n📋 Dostępne endpointy:")
    print("  GET  /")
    print("  GET  /api/health")
    print("  POST /api/create-user")
    print("  GET  /api/user/<identifier>")
    print("  GET  /api/users")
    print("  POST /api/send-message")
    print("  GET  /api/messages/<user_id>")
    print("  POST /api/message/<message_id>/read")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
