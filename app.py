# app.py - Naprawiony Flask backend z prawidłową obsługą CORS
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)

# ===== POPRAWIONA KONFIGURACJA CORS =====
CORS(app, 
     origins=['https://jurek362.github.io'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'Access-Control-Allow-Credentials'],
     supports_credentials=True
)

@app.before_request
def log_request():
    """Debug logging - usuń w produkcji"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== DODATKOWA OBSŁUGA PREFLIGHT REQUESTS =====
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "https://jurek362.github.io")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,PUT,POST,DELETE,OPTIONS")
        return response

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

@app.route('/api/create-user', methods=['POST', 'OPTIONS'])
def create_user():
    """Create new user - główny endpoint który sprawia problemy"""
    
    # Obsługa OPTIONS request (preflight)
    if request.method == 'OPTIONS':
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "https://jurek362.github.io")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "POST,OPTIONS")
        return response
    
    try:
        # Pobierz dane JSON
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        # Loguj otrzymane dane
        print(f"Otrzymane dane: {data}")
        
        # TYLKO USERNAME - jak NGL.link
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
        
        # Utwórz użytkownika - TYLKO USERNAME!
        user_data = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'tbh.fun/{username}'  # Link jak w NGL
        }
        
        # Tutaj dodaj logikę zapisu do bazy danych
        
        print(f"Użytkownik utworzony: {user_data['id']}")
        
        response = jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'data': {
                'username': user_data['username'],
                'link': user_data['link'],
                'id': user_data['id']
            }
        })
        response.status_code = 201
        return response
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Pobierz wszystkich użytkowników"""
    try:
        # Tutaj dodaj logikę pobierania z bazy danych
        users = [
            {
                'id': '1',
                'username': 'test_user',
                'link': 'tbh.fun/test_user',
                'created_at': datetime.now().isoformat()
            }
        ]
        
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

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Pobierz użytkownika po ID"""
    try:
        # Tutaj dodaj logikę pobierania z bazy danych
        user = {
            'id': user_id,
            'username': 'example_user',
            'link': f'tbh.fun/{user_id}',
            'created_at': datetime.now().isoformat()
        }
        
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

@app.route('/api/user/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Aktualizuj użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych do aktualizacji'
            }), 400
        
        # Tutaj dodaj logikę aktualizacji w bazie danych
        updated_user = {
            'id': user_id,
            **data,
            'updated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'message': 'Użytkownik zaktualizowany',
            'data': updated_user
        })
        
            except Exception as e:
        print(f"Błąd podczas aktualizacji użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Usuń użytkownika"""
    try:
        # Tutaj dodaj logikę usuwania z bazy danych
        
        print(f"Usunięto użytkownika: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Użytkownik usunięty'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania użytkownika: {str(e)}")
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
