# app.py - Kompletny Flask backend z obsługą wiadomości
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# CORS Configuration
CORS(app, origins=['https://jurek362.github.io'])

# In-memory storage (replace with real database in production)
users_db = {}  # {user_id: {id, username, created_at, link}}
messages_db = {}  # {message_id: {id, user_id, username, content, created_at, read}}

@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== USER ENDPOINTS =====

@app.route('/')
def home():
    return jsonify({
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'cors_enabled': True
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
        
        # Check if username already exists
        for user in users_db.values():
            if user['username'].lower() == username.lower():
                return jsonify({
                    'success': False,
                    'error': 'Ta nazwa użytkownika jest już zajęta'
                }), 400
        
        import re
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Create user
        user_id = str(int(datetime.now().timestamp() * 1000))
        user_data = {
            'id': user_id,
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'https://jurek362.github.io/Tbh.fun/send.html?u={username}'
        }
        
        # Save to database
        users_db[user_id] = user_data
        
        print(f"Użytkownik utworzony: {user_id} - {username}")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'data': {
                'username': user_data['username'],
                'link': user_data['link'],
                'user_id': user_data['id']  # Important: return user_id for dashboard redirect
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
        if user_id in users_db:
            return jsonify({
                'success': True,
                'data': users_db[user_id]
            })
        else:
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

@app.route('/api/user/by-username/<username>', methods=['GET'])
def get_user_by_username(username):
    """Get user by username - needed for send.html"""
    try:
        for user in users_db.values():
            if user['username'].lower() == username.lower():
                return jsonify({
                    'success': True,
                    'data': user
                })
        
        return jsonify({
            'success': False,
            'error': 'Użytkownik nie istnieje'
        }), 404
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika po username: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# ===== MESSAGE ENDPOINTS =====

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Send anonymous message to user"""
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
                'error': 'Wiadomość nie może być dłuższa niż 500 znaków'
            }), 400
        
        # Find user by username
        target_user = None
        for user in users_db.values():
            if user['username'].lower() == username.lower():
                target_user = user
                break
        
        if not target_user:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Create message
        message_id = str(uuid.uuid4())
        message_data = {
            'id': message_id,
            'user_id': target_user['id'],
            'username': target_user['username'],
            'content': message_content,
            'created_at': datetime.now().isoformat(),
            'read': False
        }
        
        # Save to database
        messages_db[message_id] = message_data
        
        print(f"Wiadomość wysłana do {username}: {message_id}")
        
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
    """Get all messages for user"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Get messages for this user
        user_messages = [
            msg for msg in messages_db.values() 
            if msg['user_id'] == user_id
        ]
        
        # Sort by creation date (newest first)
        user_messages.sort(key=lambda x: x['created_at'], reverse=True)
        
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

@app.route('/api/message/<message_id>/read', methods=['PUT'])
def mark_message_read(message_id):
    """Mark message as read"""
    try:
        if message_id not in messages_db:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie istnieje'
            }), 404
        
        # Mark as read
        messages_db[message_id]['read'] = True
        
        print(f"Wiadomość oznaczona jako przeczytana: {message_id}")
        
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

@app.route('/api/messages/<user_id>/read-all', methods=['PUT'])
def mark_all_messages_read(user_id):
    """Mark all messages as read for user"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Mark all user messages as read
        count = 0
        for message in messages_db.values():
            if message['user_id'] == user_id and not message['read']:
                message['read'] = True
                count += 1
        
        print(f"Oznaczono {count} wiadomości jako przeczytane dla użytkownika {user_id}")
        
        return jsonify({
            'success': True,
            'message': f'Oznaczono {count} wiadomości jako przeczytane'
        })
        
    except Exception as e:
        print(f"Błąd podczas oznaczania wszystkich wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/message/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    """Delete single message"""
    try:
        if message_id not in messages_db:
            return jsonify({
                'success': False,
                'error': 'Wiadomość nie istnieje'
            }), 404
        
        # Delete message
        del messages_db[message_id]
        
        print(f"Usunięto wiadomość: {message_id}")
        
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

@app.route('/api/messages/<user_id>', methods=['DELETE'])
def delete_all_messages(user_id):
    """Delete all messages for user"""
    try:
        if user_id not in users_db:
            return jsonify({
                'success': False,
                'error': 'Użytkownik nie istnieje'
            }), 404
        
        # Delete all messages for this user
        messages_to_delete = [
            msg_id for msg_id, msg in messages_db.items() 
            if msg['user_id'] == user_id
        ]
        
        for msg_id in messages_to_delete:
            del messages_db[msg_id]
        
        print(f"Usunięto {len(messages_to_delete)} wiadomości dla użytkownika {user_id}")
        
        return jsonify({
            'success': True,
            'message': f'Usunięto {len(messages_to_delete)} wiadomości'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania wszystkich wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# ===== ADMIN/DEBUG ENDPOINTS =====

@app.route('/api/debug/users', methods=['GET'])
def debug_users():
    """Debug endpoint to see all users"""
    return jsonify({
        'users': list(users_db.values()),
        'count': len(users_db)
    })

@app.route('/api/debug/messages', methods=['GET'])
def debug_messages():
    """Debug endpoint to see all messages"""
    return jsonify({
        'messages': list(messages_db.values()),
        'count': len(messages_db)
    })

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
    print("  POST /api/create-user - Tworzenie użytkownika")
    print("  GET  /api/user/<user_id> - Pobieranie użytkownika")
    print("  GET  /api/user/by-username/<username> - Pobieranie użytkownika po nazwie")
    print("  POST /api/send-message - Wysyłanie wiadomości")
    print("  GET  /api/messages/<user_id> - Pobieranie wiadomości użytkownika")
    print("  PUT  /api/message/<message_id>/read - Oznaczanie jako przeczytane")
    print("  PUT  /api/messages/<user_id>/read-all - Oznaczanie wszystkich jako przeczytane")
    print("  DELETE /api/message/<message_id> - Usuwanie wiadomości")
    print("  DELETE /api/messages/<user_id> - Usuwanie wszystkich wiadomości")
    print("  GET  /api/debug/users - Debug: wszystkie użytkownicy")
    print("  GET  /api/debug/messages - Debug: wszystkie wiadomości")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
        )
