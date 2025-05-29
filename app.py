# app.py - Naprawiony Flask backend
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# CORS configuration
CORS(app, origins=['https://jurek362.github.io'])

# Tymczasowe przechowywanie danych (w produkcji użyj prawdziwej bazy danych)
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
        
        print(f"Otrzymane dane: {data}")
        
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
            if user_data['username'] == username:
                return jsonify({
                    'success': False,
                    'error': 'Username już istnieje'
                }), 400
        
        # Utwórz użytkownika
        user_id = str(uuid.uuid4())
        user_data = {
            'id': user_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        }
        
        # Zapisz do "bazy danych"
        users_db[user_id] = user_data
        messages_db[user_id] = []  # Pusta lista wiadomości
        
        print(f"Użytkownik utworzony: {user_id}")
        
        # ZWRÓĆ DANE W POPRAWNYM FORMACIE
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'user_id': user_id,  # Dla kompatybilności z frontendem
            'link': user_data['link'],  # Bezpośrednio link
            'username': username,  # Bezpośrednio username
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

@app.route('/api/user/<username>', methods=['GET'])
def get_user_by_username(username):
    """Pobierz użytkownika po username"""
    try:
        # Znajdź użytkownika po username
        for user_id, user_data in users_db.items():
            if user_data['username'] == username:
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
        message_content = data.get('message', '').strip()
        
        if not username or not message_content:
            return jsonify({
                'success': False,
                'error': 'Username i wiadomość są wymagane'
            }), 400
        
        if len(message_content) > 500:
            return jsonify({
                'success': False,
                'error': 'Wiadomość jest za długa (max 500 znaków)'
            }), 400
        
        # Znajdź użytkownika
        target_user_id = None
        for user_id, user_data in users_db.items():
            if user_data['username'] == username:
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
        
        # Dodaj do wiadomości użytkownika
        if target_user_id not in messages_db:
            messages_db[target_user_id] = []
        
        messages_db[target_user_id].append(message)
        
        print(f"Wiadomość wysłana do {username}: {message['id']}")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość została wysłana pomyślnie!'
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
        
        # Sortuj od najnowszych
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
        
        # Znajdź wiadomość
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
        
        # Znajdź i usuń wiadomość
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
    print(f"📡 CORS włączony dla: https://jurek362.github.io")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print(f"📊 Użytkownicy w bazie: {len(users_db)}")
    print(f"💬 Wiadomości w bazie: {sum(len(msgs) for msgs in messages_db.values())}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
