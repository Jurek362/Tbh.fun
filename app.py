import os
import uuid
# import smtplib # Nieużywane, jeśli funkcjonalność e-mail jest wyłączona
# import random # Nieużywane
# from email.mime.text import MIMEText # Nieużywane
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Zmienne środowiskowe do konfiguracji serwera e-mail (obecnie nieużywane)
# EMAIL_ADDRESS = os.environ.get('EMAIL_USER')
# EMAIL_PASSWORD = os.environ.get('EMAIL_PASS')

# Prosta "baza danych" w pamięci
# UWAGA: Dane w tych słownikach są tracone po każdym restarcie aplikacji na Render.
# Do trwałego przechowywania danych rozważ użycie bazy danych (np. PostgreSQL, SQLite, Redis).
users = {}  # {user_id: {"nickname": "...", "password": "...", "verified": True/False}}
user_ids = {}  # {nickname: user_id}

@app.route('/')
def index():
    if 'user_id' in session and session['user_id'] in users:
        user_id = session['user_id']
        if users[user_id].get('verified', False):
            return render_template('home.html', nickname=users[user_id]['nickname'])
        else:
            # Ten scenariusz jest mało prawdopodobny, jeśli 'verified' jest zawsze True po rejestracji.
            return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nickname = request.form.get('nickname') # Użyj .get() dla bezpieczeństwa
        password = request.form.get('password')

        if not nickname or not password:
            return render_template('login.html', error="Wprowadź nazwę użytkownika i hasło.")

        if nickname in user_ids:
            user_id = user_ids[nickname]
            if users[user_id]['password'] == password:
                session['user_id'] = user_id
                users[user_id]['verified'] = True # Upewnij się, że jest zweryfikowany
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Błędne hasło")
        else:
            return render_template('login.html', error="Użytkownik nie istnieje")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        password = request.form.get('password')

        if not nickname or not password:
            return render_template('register.html', error="Wprowadź nazwę użytkownika i hasło.")
        
        if nickname in user_ids:
            return render_template('register.html', error="Nazwa użytkownika już zajęta")
        
        user_id = str(uuid.uuid4())
        users[user_id] = {
            "nickname": nickname,
            "password": password,
            "verified": True  # Weryfikacja e-mail pominięta
        }
        user_ids[nickname] = user_id
        
        session['user_id'] = user_id
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/check_login_status')
def check_login_status():
    if 'user_id' in session and session['user_id'] in users:
        user_id = session['user_id']
        if users[user_id].get('verified', False):
            return jsonify(logged_in=True, nickname=users[user_id]['nickname'])
    return jsonify(logged_in=False)

# Ta część jest przeznaczona do uruchamiania deweloperskiego serwera Flask.
# Na platformach produkcyjnych takich jak Render, zazwyczaj używa się serwera WSGI (np. Gunicorn).
if __name__ == '__main__':
    # Pobierz port z zmiennej środowiskowej PORT, domyślnie 5000 (standard dla Render)
    # Host 0.0.0.0 sprawia, że serwer jest dostępny z zewnątrz kontenera.
    port = int(os.environ.get('PORT', 5000))
    # Uruchomienie w trybie debug=False jest zalecane dla produkcji,
    # ale debug=True może pomóc zidentyfikować problemy na Render na początku.
    # Pamiętaj, aby ustawić debug=False po rozwiązaniu problemów.
    app.run(host='0.0.0.0', port=port, debug=True)
