# app.py - Flask backend z endpointami dla admina
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# ===== KONFIGURACJA CORS =====
CORS(app, origins=['https://jurek362.github.io'])

# ===== KONFIGURACJA ADMINA =====
ADMIN_PASSWORD = 'JPGontop'

# ===== TYMCZASOWA BAZA DANYCH W PAMIĘCI =====
# W produkcji zastąp prawdziwą bazą danych
users_db = {}
messages_db = {}

def require_admin_auth(f):
    """Decorator wymagający autoryzacji admina"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Brak autoryzacji'}), 401
        
        token = auth_header.split(' ')[1]
        if token != ADMIN_PASSWORD:
            return jsonify({'success': False, 'error': 'Nieprawidłowa autoryzacja'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

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
        
        import re
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź czy username już istnieje
        for user in users_db.values():
            if user['username'].lower() == username.lower():
                return jsonify({
                    'success': False,
                    'error': 'Ten username jest już zajęty'
                }), 400
        
        user_id = str(int(datetime.now().timestamp() * 1000))
        user_data = {
            'id': user_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'tbh.fun/{username}'
        }
        
        users_db[user_id] = user_data
        
        print(f"Użytkownik utworzony: {user_data['id']}")
        
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

# ===== MESSAGE MANAGEMENT =====

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
        
        recipient_username = data.get('recipient', '').strip()
        message_content = data.get('message', '').strip()
        
        if not recipient_username or not message_content:
            return jsonify({
                'success': False,
                'error': 'Odbiorca i wiadomość są wymagane'
            }), 400
        
        if len(message_content) > 500:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie może być dłuższa niż 500 znaków'
            }), 400
        
        # Znajdź użytkownika po username
        recipient_user = None
        for user in users_db.values():
            if user['username'].lower() == recipient_username.lower():
                recipient_user = user
                break
        
        if not recipient_user:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        message_id = str(int(datetime.now().timestamp() * 1000))
        message_data = {
            'id': message_id,
            'recipient_id': recipient_user['id'],
            'recipient_username': recipient_user['username'],
            'content': message_content,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        messages_db[message_id] = message_data
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość została wysłana!'
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
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
        
        user_messages = [msg for msg in messages_db.values() if msg['recipient_id'] == user_id]
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
        if message_id not in messages_db:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie istnieje'
            }), 404
        
        message = messages_db[message_id]
        if message['recipient_id'] != user_id:
            return jsonify({
                'success': False,
                'error': 'Brak uprawnień'
            }), 403
        
        messages_db[message_id]['read'] = True
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość oznaczona jako przeczytana'
        })
        
    except Exception as e:
        print(f"Błąd podczas oznaczania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/delete-message/<user_id>/<message_id>', methods=['DELETE'])
def delete_user_message(user_id, message_id):
    """Usuń wiadomość użytkownika"""
    try:
        if message_id not in messages_db:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie istnieje'
            }), 404
        
        message = messages_db[message_id]
        if message['recipient_id'] != user_id:
            return jsonify({
                'success': False,
                'error': 'Brak uprawnień'
            }), 403
        
        del messages_db[message_id]
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość została usunięta'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# ===== ADMIN ENDPOINTS =====

@app.route('/api/admin/stats', methods=['GET'])
@require_admin_auth
def get_admin_stats():
    """Pobierz statystyki dla admina"""
    try:
        total_users = len(users_db)
        total_messages = len(messages_db)
        unread_messages = len([msg for msg in messages_db.values() if not msg['read']])
        
        # Wiadomości dzisiaj
        today = datetime.now().date()
        today_messages = len([msg for msg in messages_db.values() 
                            if datetime.fromisoformat(msg['timestamp']).date() == today])
        
        # Średnia wiadomości na użytkownika
        avg_messages_per_user = round(total_messages / total_users, 1) if total_users > 0 else 0
        
        # Aktywni użytkownicy dzisiaj (z wiadomościami)
        active_users_today = len(set([msg['recipient_id'] for msg in messages_db.values() 
                                    if datetime.fromisoformat(msg['timestamp']).date() == today]))
        
        # Wiadomości w tym tygodniu
        week_ago = datetime.now() - timedelta(days=7)
        messages_this_week = len([msg for msg in messages_db.values() 
                                if datetime.fromisoformat(msg['timestamp']) >= week_ago])
        
        # Najaktywniejszy użytkownik
        user_message_counts = {}
        for msg in messages_db.values():
            username = msg['recipient_username']
            user_message_counts[username] = user_message_counts.get(username, 0) + 1
        
        top_user = max(user_message_counts.items(), key=lambda x: x[1])[0] if user_message_counts else '-'
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_messages': total_messages,
                'unread_messages': unread_messages,
                'today_messages': today_messages,
                'avg_messages_per_user': avg_messages_per_user,
                'active_users_today': active_users_today,
                'messages_this_week': messages_this_week,
                'top_user': top_user
            }
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania statystyk: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/messages', methods=['GET'])
@require_admin_auth
def get_all_messages():
    """Pobierz wszystkie wiadomości dla admina"""
    try:
        messages = list(messages_db.values())
        messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
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

@app.route('/api/admin/users', methods=['GET'])
@require_admin_auth
def get_all_users():
    """Pobierz wszystkich użytkowników dla admina"""
    try:
        users = list(users_db.values())
        users.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkowników: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/message/<message_id>/read', methods=['POST'])
@require_admin_auth
def admin_mark_message_read(message_id):
    """Oznacz wiadomość jako przeczytaną (admin)"""
    try:
        if message_id not in messages_db:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie istnieje'
            }), 404
        
        messages_db[message_id]['read'] = True
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość oznaczona jako przeczytana'
        })
        
    except Exception as e:
        print(f"Błąd podczas oznaczania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/message/<message_id>', methods=['DELETE'])
@require_admin_auth
def admin_delete_message(message_id):
    """Usuń wiadomość (admin)"""
    try:
        if message_id not in messages_db:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie istnieje'
            }), 404
        
        del messages_db[message_id]
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość została usunięta'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/user/<user_id>', methods=['DELETE'])
@require_admin_auth
def admin_delete_user(user_id):
    """Usuń użytkownika i wszystkie jego wiadomości (admin)"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Usuń wszystkie wiadomości użytkownika
        messages_to_delete = [msg_id for msg_id, msg in messages_db.items() 
                            if msg['recipient_id'] == user_id]
        
        for msg_id in messages_to_delete:
            del messages_db[msg_id]
        
        # Usuń użytkownika
        del users_db[user_id]
        
        return jsonify({
            'success': True,
            'message': f'Użytkownik i {len(messages_to_delete)} wiadomości zostały usunięte'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/messages/clear-old', methods=['DELETE'])
@require_admin_auth
def clear_old_messages():
    """Usuń stare wiadomości (starsze niż 30 dni)"""
    try:
        cutoff_date = datetime.now() - timedelta(days=30)
        
        messages_to_delete = [msg_id for msg_id, msg in messages_db.items() 
                            if datetime.fromisoformat(msg['timestamp']) < cutoff_date]
        
        for msg_id in messages_to_delete:
            del messages_db[msg_id]
        
        return jsonify({
            'success': True,
            'message': f'Usunięto {len(messages_to_delete)} starych wiadomości'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania starych wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/messages/clear-all', methods=['DELETE'])
@require_admin_auth
def clear_all_messages():
    """Usuń wszystkie wiadomości (admin)"""
    try:
        count = len(messages_db)
        messages_db.clear()
        
        return jsonify({
            'success': True,
            'message': f'Usunięto wszystkie {count} wiadomości'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania wszystkich wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/users/clear-all', methods=['DELETE'])
@require_admin_auth
def clear_all_users():
    """Usuń wszystkich użytkowników i wiadomości (admin)"""
    try:
        user_count = len(users_db)
        message_count = len(messages_db)
        
        users_db.clear()
        messages_db.clear()
        
        return jsonify({
            'success': True,
            'message': f'Usunięto {user_count} użytkowników i {message_count} wiadomości'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania wszystkich użytkowników: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/admin/export', methods=['GET'])
@require_admin_auth
def export_data():
    """Eksportuj wszystkie dane (admin)"""
    try:
        export_data = {
            'users': list(users_db.values()),
            'messages': list(messages_db.values()),
            'export_date': datetime.now().isoformat(),
            'stats': {
                'total_users': len(users_db),
                'total_messages': len(messages_db)
            }
        }
        
        return jsonify({
            'success': True,
            'data': export_data
        })
        
    except Exception as e:
        print(f"Błąd podczas eksportu danych: {str(e)}")
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
    print(f"🔐 Admin endpoints dostępne")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
)
