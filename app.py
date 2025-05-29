from flask import Flask, request, jsonify, redirect, url_for
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

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

@app.route('/')
def index():
    """Strona główna"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Brak pliku index.html", 404

@app.route('/dashboard')
def dashboard():
    """Dashboard użytkownika"""
    user = request.args.get('user')
    if not user:
        return redirect(url_for('index'))
    
    data = load_data()
    if user not in data['users']:
        return redirect(url_for('index'))
    
    try:
        with open('dashboard.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Brak pliku dashboard.html", 404

@app.route('/send')
def send_message_page():
    """Strona wysyłania wiadomości"""
    to_user = request.args.get('to')
    if not to_user:
        return redirect(url_for('index'))
    
    data = load_data()
    if to_user not in data['users']:
        return redirect(url_for('index'))
    
    try:
        with open('send.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Brak pliku send.html", 404

@app.route('/register', methods=['POST'])
def register():
    """Rejestracja nowego użytkownika"""
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

@app.route('/send_message', methods=['POST'])
def send_message():
    """Wyślij wiadomość do użytkownika"""
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
