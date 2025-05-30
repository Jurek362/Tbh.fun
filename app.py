# app.py - Kompletny Flask backend z endpointami dla wiadomości
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# ===== KONFIGURACJA CORS =====
CORS(app, origins=['https://jurek362.github.io'])

# ===== TYMCZASOWA BAZA DANYCH W PAMIĘCI =====
# W produkcji zastąp prawdziwą bazą danych
users_db = {}
messages_db = {}

@app.before_request
def log_request():
    """Debug logging - usuń w produkcji"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== BASIC ROUTES =====

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

# ===== USER ROUTES =====

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
        
        # Sprawdź czy username już istnieje
        for user_id, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
                return jsonify({
                    'success': False,
                    'error': 'Username już istnieje'
                }), 400
        
        import re
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Utwórz użytkownika
        user_id = str(uuid.uuid4())
        user_data = {
            'id': user_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'tbh.fun/{username}'
        }
        
        # Zapisz do "bazy danych"
        users_db[user_id] = user_data
        messages_db[user_id] = []
        
        print(f"Użytkownik utworzony: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'data': {
                'username': user_data['username'],
                'link': user_data['link'],
                'id': user_data['id']
            }
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Pobierz użytkownika po ID"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        return jsonify({
            'success': True,
            'data': users_db[user_id]
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/by-username/<username>', methods=['GET'])
def get_user_by_username(username):
    """Pobierz użytkownika po username"""
    try:
        for user_id, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
                return jsonify({
                    'success': True,
                    'data': user_data
                })
        
        return jsonify({
            'success': False,
            'error': 'Użytkownik nie istnieje'
        }), 404
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# ===== MESSAGE ROUTES =====

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
        content = data.get('message', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username jest wymagany'
            }), 400
        
        if not content:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie może być pusta'
            }), 400
        
        if len(content) > 1000:
            return jsonify({
                'success': False,
                'error': 'Wiadomość jest za długa (max 1000 znaków)'
            }), 400
        
        # Znajdź użytkownika
        user_id = None
        for uid, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
                user_id = uid
                break
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Utwórz wiadomość
        message = {
            'id': str(uuid.uuid4()),
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        # Dodaj do "bazy danych"
        if user_id not in messages_db:
            messages_db[user_id] = []
        
        messages_db[user_id].append(message)
        
        print(f"Wiadomość wysłana do {username}: {message['id']}")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość wysłana pomyślnie!'
        }), 201
        
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
            'messages': user_messages,
            'count': len(user_messages)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/mark-read/<user_id>/<message_id>', methods=['POST'])
def mark_message_as_read(user_id, message_id):
    """Oznacz wiadomość jako przeczytaną"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(user_id, [])
        
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

@app.route('/api/delete-message/<user_id>/<message_id>', methods=['DELETE'])
def delete_message(user_id, message_id):
    """Usuń wiadomość"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(user_id, [])
        
        for i, message in enumerate(user_messages):
            if message['id'] == message_id:
                del user_messages[i]
                return jsonify({
                    'success': True,
                    'message': 'Wiadomość usunięta'
                })
        
        return jsonify({
            'success': False,
            'error': 'Wiadomość nie istnieje'
        }), 404
        
    except Exception as e:
        print(f"Błąd podczas usuwania wiadomości: {str(e)}")
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
    print("📝 Dostępne endpointy:")
    print("  - POST /api/create-user")
    print("  - GET /api/user/<user_id>")
    print("  - GET /api/user/by-username/<username>")
    print("  - POST /api/send-message")
    print("  - GET /api/messages/<user_id>")
    print("  - POST /api/mark-read/<user_id>/<message_id>")
    print("  - DELETE /api/delete-message/<user_id>/<message_id>")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
        )
