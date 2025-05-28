from flask import Flask, request, jsonify
from flask_cors import CORS
import secrets
from datetime import datetime
import os

app = Flask(__name__)

# CORS configuration
CORS(app, origins=['https://tbh-fun.onrender.com', 'jurek362.github.io/tbh.fun'], 
     supports_credentials=True)

# In-memory storage (w produkcji użyj prawdziwej bazy danych jak PostgreSQL)
users = {}
messages = {}

def generate_user_id():
    """Generuj unikalny ID użytkownika"""
    return secrets.token_hex(8)

def generate_message_id():
    """Generuj unikalny ID wiadomości"""
    return secrets.token_hex(12)

@app.route('/api/create-user', methods=['POST'])
def create_user():
    """Endpoint do tworzenia nowego użytkownika/linku"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username or len(username) < 3:
        return jsonify({'error': 'Username musi mieć co najmniej 3 znaki'}), 400
    
    # Sprawdź czy username już istnieje
    for user_id, user in users.items():
        if user['username'].lower() == username.lower():
            return jsonify({'error': 'Ta nazwa użytkownika jest już zajęta'}), 400
    
    user_id = generate_user_id()
    user = {
        'id': user_id,
        'username': username,
        'created_at': datetime.now().isoformat(),
        'message_count': 0
    }
    
    users[user_id] = user
    messages[user_id] = []
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'username': username,
        'link': f'{request.scheme}://{request.host}/u/{username}'
    })

@app.route('/api/user/<username>', methods=['GET'])
def get_user(username):
    """Endpoint do pobierania informacji o użytkowniku"""
    found_user = None
    for user_id, user in users.items():
        if user['username'].lower() == username.lower():
            found_user = user
            break
    
    if not found_user:
        return jsonify({'error': 'Użytkownik nie został znaleziony'}), 404
    
    return jsonify({
        'username': found_user['username'],
        'message_count': found_user['message_count']
    })

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Endpoint do wysyłania anonimowej wiadomości"""
    data = request.get_json()
    username = data.get('username', '').strip()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Wiadomość nie może być pusta'}), 400
    
    if len(message) > 500:
        return jsonify({'error': 'Wiadomość jest zbyt długa (max 500 znaków)'}), 400
    
    # Znajdź użytkownika
    found_user = None
    user_id = None
    for uid, user in users.items():
        if user['username'].lower() == username.lower():
            found_user = user
            user_id = uid
            break
    
    if not found_user:
        return jsonify({'error': 'Użytkownik nie został znaleziony'}), 404
    
    # Dodaj wiadomość
    message_obj = {
        'id': generate_message_id(),
        'content': message,
        'timestamp': datetime.now().isoformat(),
        'read': False
    }
    
    user_messages = messages.get(user_id, [])
    user_messages.insert(0, message_obj)  # Dodaj na początek (najnowsze pierwsze)
    messages[user_id] = user_messages
    
    # Zaktualizuj licznik wiadomości
    found_user['message_count'] = len(user_messages)
    users[user_id] = found_user
    
    return jsonify({'success': True, 'message': 'Wiadomość została wysłana!'})

@app.route('/api/messages/<user_id>', methods=['GET'])
def get_messages(user_id):
    """Endpoint do pobierania wiadomości użytkownika"""
    if user_id not in users:
        return jsonify({'error': 'Użytkownik nie został znaleziony'}), 404
    
    user_messages = messages.get(user_id, [])
    return jsonify({
        'messages': user_messages,
        'total': len(user_messages)
    })

@app.route('/api/mark-read/<user_id>/<message_id>', methods=['POST'])
def mark_message_read(user_id, message_id):
    """Endpoint do oznaczania wiadomości jako przeczytanej"""
    if user_id not in users:
        return jsonify({'error': 'Użytkownik nie został znaleziony'}), 404
    
    user_messages = messages.get(user_id, [])
    for message in user_messages:
        if message['id'] == message_id:
            message['read'] = True
            break
    
    messages[user_id] = user_messages
    return jsonify({'success': True})

@app.route('/api/delete-message/<user_id>/<message_id>', methods=['DELETE'])
def delete_message(user_id, message_id):
    """Endpoint do usuwania wiadomości"""
    if user_id not in users:
        return jsonify({'error': 'Użytkownik nie został znaleziony'}), 404
    
    user_messages = messages.get(user_id, [])
    user_messages = [msg for msg in user_messages if msg['id'] != message_id]
    messages[user_id] = user_messages
    
    # Zaktualizuj licznik
    users[user_id]['message_count'] = len(user_messages)
    
    return jsonify({'success': True})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint dla Render"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/')
def home():
    """Główna strona API"""
    return jsonify({
        'message': 'NGL Clone API',
        'version': '1.0.0',
        'endpoints': {
            'create_user': '/api/create-user',
            'get_user': '/api/user/<username>',
            'send_message': '/api/send-message',
            'get_messages': '/api/messages/<user_id>',
            'mark_read': '/api/mark-read/<user_id>/<message_id>',
            'delete_message': '/api/delete-message/<user_id>/<message_id>'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
