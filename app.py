import os
import uuid
import smtplib
import random
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24) # Ustaw losowy klucz sesji

# Zmienne środowiskowe do konfiguracji serwera e-mail
# EMAIL_ADDRESS = os.environ.get('EMAIL_USER')
# EMAIL_PASSWORD = os.environ.get('EMAIL_PASS')

# Prosta "baza danych" w pamięci
users = {} # {user_id: {"nickname": "...", "password": "...", "verified": True}}
user_ids = {} # {nickname: user_id}
# verification_codes = {} # {user_id: code}
sessions = {} # {session_id: user_id}

@app.route('/')
def index():
    if 'user_id' in session and session['user_id'] in users:
        user_id = session['user_id']
        if users[user_id].get('verified', False): # Sprawdzamy, czy użytkownik jest zweryfikowany
            return render_template('home.html', nickname=users[user_id]['nickname'])
        else:
            return redirect(url_for('login')) # Przekieruj na stronę logowania, jeśli niezweryfikowany
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nickname = request.form['nickname']
        password = request.form['password']
        if nickname in user_ids:
            user_id = user_ids[nickname]
            if users[user_id]['password'] == password:
                # Jeśli użytkownik istnieje i hasło się zgadza
                # W usuniętej wersji była tu weryfikacja maila.
                # Teraz logujemy od razu.
                session['user_id'] = user_id
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Błędne hasło")
        else:
            return render_template('login.html', error="Użytkownik nie istnieje")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nickname = request.form['nickname']
        password = request.form['password']
        # email = request.form['email'] # Adres e-mail nie jest już używany
        
        if nickname in user_ids:
            return render_template('register.html', error="Nazwa użytkownika już zajęta")
        
        # Generuj nowy ID dla użytkownika
        user_id = str(uuid.uuid4())
        
        users[user_id] = {
            "nickname": nickname,
            "password": password,
            # "email": email, # Nie przechowujemy już adresu e-mail
            "verified": True # Ustawiamy na True, ponieważ weryfikacja mailowa jest pominięta
        }
        user_ids[nickname] = user_id

        # # Generowanie i wysyłanie kodu weryfikacyjnego - USUNIĘTE
        # verification_code = str(random.randint(100000, 999999))
        # verification_codes[user_id] = verification_code
        
        # msg = MIMEText(f"Twój kod weryfikacyjny: {verification_code}")
        # msg['Subject'] = 'Kod weryfikacyjny TBH.fun'
        # msg['From'] = EMAIL_ADDRESS
        # msg['To'] = email

        # try:
        #     with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        #         smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        #         smtp.send_message(msg)
        #     return redirect(url_for('verify_email', user_id=user_id))
        # except Exception as e:
        #     print(f"Błąd wysyłania maila: {e}")
        #     return render_template('register.html', error="Błąd podczas wysyłania e-maila weryfikacyjnego. Spróbuj ponownie później.")
        
        # Po rejestracji i pominięciu weryfikacji, logujemy od razu
        session['user_id'] = user_id
        return redirect(url_for('index'))
    return render_template('register.html')

# # Usunięta trasa do weryfikacji e-mail
# @app.route('/verify_email/<user_id>', methods=['GET', 'POST'])
# def verify_email(user_id):
#     if request.method == 'POST':
#         code = request.form['code']
#         if user_id in verification_codes and verification_codes[user_id] == code:
#             users[user_id]['verified'] = True
#             del verification_codes[user_id]
#             session['user_id'] = user_id
#             return redirect(url_for('index'))
#         else:
#             return render_template('verify_email.html', user_id=user_id, error="Nieprawidłowy kod weryfikacyjny")
#     return render_template('verify_email.html', user_id=user_id)

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
    # Upewnij się, że masz ustawione zmienne środowiskowe EMAIL_USER i EMAIL_PASS
    # dla oryginalnej wersji. Dla tej wersji nie są one potrzebne.
    app.run(debug=True) # debug=True w trybie deweloperskim
