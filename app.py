# app.py - Naprawiony Flask backend z pełną obsługą CORS
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)

# ===== KONFIGURACJA CORS - ROZSZERZONA =====
CORS(app, 
     origins=['https://jurek362.github.io'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'Accept'],
     supports_credentials=True)

# Dodatkowe nagłówki CORS dla wszystkich odpowiedzi
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://jurek362.github.io')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Tymczasowa baza danych w pamięci z przykładowymi danymi
users_db = {
    'jurekl131': {
        'id': '1000000000000',
        'username': 'Jurekl131',
        'created_at': '2024-01-01T00:00:00',
        'link': 'https://jurek362.github.io/Tbh.fun/send.html?u=Jurekl131',
        'message_count': 0
    },
    'testuser': {
        'id': '1000000000001',
        'username': 'testuser',
        'created_at': '2024-01-01T00:00:00',
        'link': 'https://jurek362.github.io/Tbh.fun/send.html?u=testuser',
        'message_count': 0
    }
}
messages_db = {
    'jurekl131': [],
    'testuser': []
}

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
        'endpoints': [
            '/api/health',
            '/api/create-user',
            '/api/user/<username>',
            '/api/send-message'
        ]
    })

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'users_count': len(users_db),
        'messages_count': len(messages_db)
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
        
        # Walidacja username
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
        
        import re
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź czy username już istnieje
        if username.lower() in users_db:
            return jsonify({
                'success': False,
                'error': 'Username już istnieje'
            }), 409
        
        # Utwórz użytkownika
        user_data = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'https://jurek362.github.io/Tbh.fun/send.html?u={username}',
            'message_count': 0
        }
        
        # Zapisz do "bazy danych"
        users_db[username.lower()] = user_data
        messages_db[username.lower()] = []
        
        print(f"Użytkownik utworzony: {username}")
        
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

@app.route('/api/user/<username>', methods=['GET'])
def get_user_by_username(username):
    """Pobierz użytkownika po username - NAPRAWIONY ENDPOINT"""
    try:
        username_lower = username.lower()
        
        print(f"Szukam użytkownika: '{username}' (lowercase: '{username_lower}')")
        print(f"Użytkownicy w bazie: {list(users_db.keys())}")
        
        if username_lower not in users_db:
            return jsonify({
                'success': False,
                'error': f'Użytkownik "{username}" nie istnieje',
                'available_users': list(users_db.keys())
            }), 404
        
        user = users_db[username_lower]
        
        return jsonify({
            'success': True,
            'data': user,
            'message': f'Użytkownik {username} istnieje'
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Wyślij anonimową wiadomość - BRAKUJĄCY ENDPOINT"""
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
                'error': 'Wiadomość jest za długa (max 500 znaków)'
            }), 400
        
        username_lower = username.lower()
        
        # Sprawdź czy użytkownik istnieje
        if username_lower not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Utwórz wiadomość
        message_data = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'recipient': username
        }
        
        # Zapisz wiadomość
        if username_lower not in messages_db:
            messages_db[username_lower] = []
        
        messages_db[username_lower].append(message_data)
        
        # Aktualizuj licznik wiadomości użytkownika
        users_db[username_lower]['message_count'] = len(messages_db[username_lower])
        
        print(f"Nowa wiadomość dla {username}: {message[:50]}...")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość została wysłana pomyślnie!',
            'message_id': message_data['id']
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/messages/<username>', methods=['GET'])
def get_user_messages(username):
    """Pobierz wiadomości użytkownika"""
    try:
        username_lower = username.lower()
        
        if username_lower not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        user_messages = messages_db.get(username_lower, [])
        
        return jsonify({
            'success': True,
            'data': user_messages,
            'count': len(user_messages)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/users', methods=['GET'])
def get_all_users():
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

# ===== OBSŁUGA PREFLIGHT OPTIONS =====
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Obsługa żądań preflight OPTIONS"""
    return '', 200

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint nie istnieje',
        'path': request.path,
        'available_endpoints': [
            '/',
            '/api/health',
            '/api/create-user',
            '/api/user/<username>',
            '/api/send-message',
            '/api/messages/<username>',
            '/api/users'
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
    print(f"📋 Dostępne endpointy:")
    print("   GET  / - Strona główna API")
    print("   GET  /api/health - Status serwera")
    print("   POST /api/create-user - Tworzenie użytkownika")
    print("   GET  /api/user/<username> - Pobieranie użytkownika")
    print("   POST /api/send-message - Wysyłanie wiadomości")
    print("   GET  /api/messages/<username> - Pobieranie wiadomości")
    print("   GET  /api/users - Lista wszystkich użytkowników")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
        )
