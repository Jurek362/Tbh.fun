from flask import Flask, request, jsonify, redirect, url_for
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

# Obsługa CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Plik do przechowywania danych
DATA_FILE = 'data.json'

def load_data():
    """Załaduj dane z pliku JSON"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return {'users': {}, 'messages': {}}

def save_data(data):
    """Zapisz dane do pliku JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_valid_username(username):
    """Sprawdź czy nazwa użytkownika jest prawidłowa"""
    if not username or len(username) < 2 or len(username) > 30:
        return False
    return re.match(r'^[a-zA-Z0-9_-]+$', username) is not None

# API endpoints only - HTML obsługiwane przez GitHub Pages

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Rejestracja nowego użytkownika"""
    if request.method == 'GET':
        return jsonify({'success': False, 'message': 'Use POST method'})
    
    # Obsługa JSON i form data
    if request.is_json:
        username = request.json.get('username', '').strip().lower()
    else:
        username = request.form.get('username', '').strip().lower()
    
    if not is_valid_username(username):
        return jsonify({
            'success': False, 
            'message': 'Nieprawidłowa nazwa użytkownika. Użyj 2-30 znaków (litery, cyfry, - lub _)'
        })
    
    data = load_data()
    
    if username in data['users']:
        return jsonify({
            'success': False, 
            'message': 'Ta nazwa użytkownika jest już zajęta'
        })
    
    # Stwórz nowego użytkownika
    data['users'][username] = {
        'created_at': datetime.now().isoformat(),
        'message_count': 0
    }
    
    # Inicjalizuj listę wiadomości dla użytkownika
    if username not in data['messages']:
        data['messages'][username] = []
    
    save_data(data)
    
    return jsonify({
        'success': True,
        'message': 'Konto zostało utworzone pomyślnie'
    })

@app.route('/send_message', methods=['GET', 'POST'])
def send_message():
    """Wyślij wiadomość do użytkownika"""
    if request.method == 'GET':
        return jsonify({'success': False, 'message': 'Use POST method'})
    
    # Obsługa JSON i form data
    if request.is_json:
        to_user = request.json.get('to', '').strip().lower()
        message_content = request.json.get('message', '').strip()
    else:
        to_user = request.form.get('to', '').strip().lower()
        message_content = request.form.get('message', '').strip()
    
    if not to_user or not message_content:
        return jsonify({
            'success': False,
            'message': 'Brak odbiorcy lub wiadomości'
        })
    
    if len(message_content) > 1000:
        return jsonify({
            'success': False,
            'message': 'Wiadomość jest za długa (max 1000 znaków)'
        })
    
    data = load_data()
    
    if to_user not in data['users']:
        return jsonify({
            'success': False,
            'message': 'Użytkownik nie istnieje'
        })
    
    # Dodaj wiadomość
    message = {
        'content': message_content,
        'timestamp': datetime.now().isoformat(),
        'id': len(data['messages'].get(to_user, [])) + 1
    }
    
    if to_user not in data['messages']:
        data['messages'][to_user] = []
    
    data['messages'][to_user].append(message)
    data['users'][to_user]['message_count'] = len(data['messages'][to_user])
    
    save_data(data)
    
    return jsonify({
        'success': True,
        'message': 'Wiadomość została wysłana'
    })

@app.route('/messages')
def get_messages():
    """Pobierz wiadomości użytkownika"""
    user = request.args.get('user', '').strip().lower()
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'Brak nazwy użytkownika'
        })
    
    data = load_data()
    
    if user not in data['users']:
        return jsonify({
            'success': False,
            'message': 'Użytkownik nie istnieje'
        })
    
    messages = data['messages'].get(user, [])
    # Sortuj wiadomości od najnowszych
    messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({
        'success': True,
        'messages': messages
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
