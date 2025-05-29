from flask import Flask, render_template, request, jsonify, redirect, url_for
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
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard użytkownika"""
    user = request.args.get('user')
    if not user:
        return redirect(url_for('index'))
    
    data = load_data()
    if user not in data['users']:
        return redirect(url_for('index'))
    
    return render_template('dashboard.html')

@app.route('/send')
def send_message_page():
    """Strona wysyłania wiadomości"""
    to_user = request.args.get('to')
    if not to_user:
        return redirect(url_for('index'))
    
    data = load_data()
    if to_user not in data['users']:
        return redirect(url_for('index'))
    
    return render_template('send.html')

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
    
    # Stwórz nowego uż
