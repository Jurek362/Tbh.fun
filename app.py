import os
import uuid
import random
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS # Nowy import dla obsługi CORS

# Zmodyfikuj inicjalizację Flask, aby wskazać bieżący katalog jako folder szablonów.
# Zakładamy, że pliki HTML (index.html, home.html, login.html, register.html)
# znajdują się w tym samym katalogu co ten skrypt Pythona.
app = Flask(__name__, template_folder='.') # <-- TUTAJ ZMIANA: '.' oznacza bieżący katalog

app.secret_key = os.urandom(24) # Ustaw losowy klucz sesji

# Konfiguracja CORS: Zezwól na żądania z konkretnej domeny dla tras zaczynających się od /api/
# Zastąp "https://jurek362.github.io" domeną Twojego frontendu, jeśli jest inna.
CORS(app, resources={r"/api/*": {"origins": "https://jurek362.github.io"}})

# Prosta "baza danych" w pamięci
users = {} # {user_id: {"nickname": "...", "password": "...", "verified": True}}
user_ids = {} # {nickname: user_id}
sessions = {} # {session_id: user_id}

@app.route('/')
def index():
    if 'user_id' in session and session['user_id'] in users:
        user_id = session['user_id']
        if users[user_id].get('verified', False):
            return render_template('home.html', nickname=users[user_id]['nickname'])
        else:
            return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nickname = request.form['nickname']
        password = request.form['password']
        if nickname in user_ids:
            user_id = user_ids[nickname]
            if users[user_id]['password'] == password:
                session['user_id'] = user_id
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Błędne hasło")
        else:
            return render_template('login.html', error="Użytkownik nie istnieje")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Ta trasa służy do rejestracji poprzez formularz HTML
    if request.method == 'POST':
        nickname = request.form['nickname']
        password = request.form['password']
        
        if nickname in user_ids:
            return render_template('register.html', error="Nazwa użytkownika już zajęta")
        
        user_id = str(uuid.uuid4())
        
        users[user_id] = {
            "nickname": nickname,
            "password": password,
            "verified": True # Weryfikacja mailowa jest pominięta
        }
        user_ids[nickname] = user_id

        session['user_id'] = user_id
        return redirect(url_for('index'))
    return render_template('register.html')

# TRASA API do tworzenia użytkowników z frontendu (np. JavaScript)
@app.route('/api/create-user', methods=['POST'])
def api_create_user():
    # Oczekujemy danych w formacie JSON
    data = request.get_json()
    if not data:
        return jsonify({"error": "Brak danych JSON w żądaniu"}), 400 # Bad Request

    nickname = data.get('nickname')
    password = data.get('password')

    if not nickname or not password:
        return jsonify({"error": "Pseudonim i hasło są wymagane"}), 400

    if nickname in user_ids:
        return jsonify({"error": "Nazwa użytkownika już zajęta"}), 409 # Conflict

    user_id = str(uuid.uuid4())
    users[user_id] = {
        "nickname": nickname,
        "password": password,
        "verified": True # Weryfikacja mailowa jest pominięta
    }
    user_ids[nickname] = user_id

    # Zwracamy odpowiedź JSON zamiast przekierowania
    return jsonify({
        "message": "Użytkownik zarejestrowany pomyślnie",
        "user_id": user_id,
        "nickname": nickname
    }), 201 # Created

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/check_login_status')
def check_login_status():
    if 'user_id' in session and session['user_id'] in users:
        return jsonify(logged_in=True, nickname=users[session['user_id']]['nickname'])
    return jsonify(logged_in=False)

if __name__ == '__main__':
    app.run(debug=True)

