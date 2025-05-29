# app.py - Naprawiony Flask backend
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# KONFIGURACJA CORS
CORS(app, origins=['https://jurek362.github.io', 'https://tbh-fun.onrender.com'])

# SYMULACJA BAZY DANYCH (w produkcji użyj prawdziwej bazy)
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
        
        # Sprawdź czy username zawiera tylko dozwolone znaki
        import re
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
                }), 409
        
        # Utwórz użytkownika
        user_id = str(uuid.uuid4())
        user_data = {
            'id': user_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        }
        
        users_db[user_id] = user_data
        messages_db[user_id] = []
        
        print(f"Użytkownik utworzony: {user_id} - {username}")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'user_id': user_id,
            'username': username,
            'link': user_data['link']
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/<username>', methods=['GET'])
def check_user_exists(username):
    """Sprawdź czy użytkownik istnieje (po username)"""
    try:
        for user_id, user_data in users_db.items():
            if user_data['username'].lower() == username.lower():
                return jsonify({
                    'success': True,
                    'exists': True,
                    'user_id': user_id,
                    'username': user_data['username']
                })
        
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
        
        # Dodaj wiadomość
        message_data = {
            'id': str(uuid.uuid4()),
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        messages_db[user_id].append(message_data)
        
        print(f"Wiadomość wysłana do {username}: {message[:50]}...")
        
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

@app.route('/api/user/<user_id>/messages', methods=['GET'])
def get_user_messages(user_id):
    """Pobierz wiadomości użytkownika"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(user_id, [])
        
        # Oznacz wiadomości jako przeczytane
        for msg in user_messages:
            msg['read'] = True
        
        return jsonify({
            'success': True,
            'messages': user_messages,
            'count': len(user_messages),
            'username': users_db[user_id]['username']
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/<user_id>/info', methods=['GET'])
def get_user_info(user_id):
    """Pobierz informacje o użytkowniku"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_data = users_db[user_id]
        message_count = len(messages_db.get(user_id, []))
        unread_count = len([msg for msg in messages_db.get(user_id, []) if not msg.get('read', False)])
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_data['id'],
                'username': user_data['username'],
                'created_at': user_data['created_at'],
                'link': user_data['link'],
                'message_count': message_count,
                'unread_count': unread_count
            }
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania informacji o użytkowniku: {str(e)}")
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
