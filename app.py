# app.py - Flask backend z dodanymi endpointami dla frontendu
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

# CORS konfiguracja
CORS(app, origins=['https://jurek362.github.io'])

# Tymczasowa "baza danych" w pamięci (w produkcji użyj prawdziwej bazy)
users_db = {}

@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== GŁÓWNE ENDPOINTY DLA FRONTENDU =====

@app.route('/register', methods=['POST'])
def register():
    """Endpoint dla logowania/rejestracji - używany przez frontend"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        
        # Walidacja
        if not username:
            return jsonify({
                'success': False,
                'message': 'Username jest wymagany'
            }), 400
        
        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': 'Username musi mieć przynajmniej 3 znaki'
            }), 400
        
        if len(username) > 20:
            return jsonify({
                'success': False,
                'message': 'Username nie może być dłuższy niż 20 znaków'
            }), 400
        
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'message': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź czy użytkownik już istnieje
        is_existing_user = username in users_db
        
        if not is_existing_user:
            # Utwórz nowego użytkownika
            users_db[username] = {
                'id': str(int(datetime.now().timestamp() * 1000)),
                'username': username,
                'created_at': datetime.now().isoformat(),
                'link': f'tbh.fun/{username}',
                'messages': []
            }
        
        print(f"Użytkownik {'zalogowany' if is_existing_user else 'utworzony'}: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Zalogowano pomyślnie!' if is_existing_user else 'Konto utworzone!',
            'isNew': not is_existing_user,
            'data': {
                'username': username,
                'link': f'tbh.fun/{username}'
            }
        }), 200
        
    except Exception as e:
        print(f"Błąd podczas rejestracji: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

@app.route('/check_user', methods=['GET'])
def check_user():
    """Sprawdź czy użytkownik istnieje - używane przy automatycznym logowaniu"""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'exists': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
        exists = username in users_db
        
        return jsonify({
            'exists': exists,
            'username': username if exists else None
        })
        
    except Exception as e:
        print(f"Błąd podczas sprawdzania użytkownika: {str(e)}")
        return jsonify({
            'exists': False,
            'error': 'Błąd serwera'
        }), 500

# ===== ENDPOINTY DLA WIADOMOŚCI =====

@app.route('/send_message', methods=['POST'])
def send_message():
    """Wyślij anonimową wiadomość do użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych'
            }), 400
        
        recipient = data.get('recipient', '').strip()
        message = data.get('message', '').strip()
        
        if not recipient or not message:
            return jsonify({
                'success': False,
                'message': 'Odbiorca i wiadomość są wymagane'
            }), 400
        
        if len(message) > 500:
            return jsonify({
                'success': False,
                'message': 'Wiadomość nie może być dłuższa niż 500 znaków'
            }), 400
        
        # Sprawdź czy odbiorca istnieje
        if recipient not in users_db:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        # Dodaj wiadomość
        new_message = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        users_db[recipient]['messages'].append(new_message)
        
        print(f"Wiadomość wysłana do {recipient}")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość wysłana!'
        })
        
    except Exception as e:
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """Pobierz wiadomości użytkownika"""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
        if username not in users_db:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        messages = users_db[username]['messages']
        
        # Oznacz wiadomości jako przeczytane
        for msg in messages:
            msg['read'] = True
        
        return jsonify({
            'success': True,
            'messages': messages,
            'count': len(messages)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

# ===== POZOSTAŁE ENDPOINTY =====

@app.route('/')
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'endpoints': {
            'register': 'POST /register',
            'check_user': 'GET /check_user?user=USERNAME',
            'send_message': 'POST /send_message',
            'get_messages': 'GET /get_messages?user=USERNAME'
        }
    })

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'users_count': len(users_db)
    })

# ===== STARE ENDPOINTY (dla kompatybilności) =====

@app.route('/api/create-user', methods=['POST'])
def create_user():
    """Stary endpoint - przekierowanie na nowy"""
    return register()

@app.route('/api/users', methods=['GET'])
def get_users():
    """Pobierz wszystkich użytkowników (dla admina)"""
    try:
        users_list = []
        for username, data in users_db.items():
            users_list.append({
                'username': username,
                'created_at': data['created_at'],
                'messages_count': len(data['messages'])
            })
        
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

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint nie istnieje',
        'path': request.path,
        'available_endpoints': [
            'POST /register',
            'GET /check_user',
            'POST /send_message',
            'GET /get_messages'
        ]
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
    print("📋 Dostępne endpointy:")
    print("   POST /register - rejestracja/logowanie")
    print("   GET /check_user?user=USERNAME - sprawdź użytkownika")
    print("   POST /send_message - wyślij wiadomość")
    print("   GET /get_messages?user=USERNAME - pobierz wiadomości")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
        )
