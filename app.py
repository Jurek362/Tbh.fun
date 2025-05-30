# app.py - Kompletny Flask backend z obsługą wiadomości
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)

# Konfiguracja CORS
CORS(app, origins=['https://jurek362.github.io', 'http://localhost:3000', 'http://127.0.0.1:5000'])

# Tymczasowe przechowywanie danych (w produkcji użyj prawdziwej bazy danych)
users_db = {}
messages_db = {}

@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== USER ROUTES =====

@app.route('/')
def home():
    return jsonify({
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'endpoints': [
            '/api/create-user',
            '/api/user/<user_id>',
            '/api/send-message',
            '/api/messages/<user_id>',
            '/api/mark-read/<user_id>/<message_id>',
            '/api/delete-message/<user_id>/<message_id>'
        ]
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/create-user', methods=['POST'])
def create_user():
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
        for user in users_db.values():
            if user['username'].lower() == username.lower():
                return jsonify({
                    'success': False,
                    'error': 'Ta nazwa użytkownika już istnieje'
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
            'link': f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        }
        
        # Zapisz użytkownika
        users_db[user_id] = user_data
        messages_db[user_id] = []  # Pusta lista wiadomości
        
        print(f"Użytkownik utworzony: {user_id} ({username})")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'data': {
                'id': user_id,
                'username': username,
                'link': user_data['link']
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
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user = users_db[user_id]
        
        return jsonify({
            'success': True,
            'data': user
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/by-username/<username>', methods=['GET'])
def get_user_by_username(username):
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
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        message_content = data.get('message', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username jest wymagany'
            }), 400
        
        if not message_content:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie może być pusta'
            }), 400
        
        if len(message_content) > 500:
            return jsonify({
                'success': False,
                'error': 'Wiadomość jest za długa (max 500 znaków)'
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
        message = {
            'id': str(uuid.uuid4()),
            'content': message_content,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        # Dodaj wiadomość do użytkownika
        if target_user_id not in messages_db:
            messages_db[target_user_id] = []
        
        messages_db[target_user_id].append(message)
        
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
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(user_id, [])
        
        # Znajdź i oznacz wiadomość jako przeczytaną
        for message in user_messages:
            if message['id'] == message_id:
                message['read'] = True
                print(f"Wiadomość {message_id} oznaczona jako przeczytana")
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
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(user_id, [])
        
        # Znajdź i usuń wiadomość
        for i, message in enumerate(user_messages):
            if message['id'] == message_id:
                del user_messages[i]
                print(f"Wiadomość {message_id} usunięta")
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

# ===== STATISTICS =====

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_users = len(users_db)
        total_messages = sum(len(messages) for messages in messages_db.values())
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'total_messages': total_messages,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania statystyk: {str(e)}")
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
    print(f"📡 CORS włączony dla GitHub Pages")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print(f"📬 Endpointy wiadomości: AKTYWNE")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
        )
