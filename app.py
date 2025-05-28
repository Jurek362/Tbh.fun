import os
import uuid
import random
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS

# Zmodyfikuj inicjalizację Flask, aby wskazać bieżący katalog jako folder szablonów.
app = Flask(__name__, template_folder='.')

app.secret_key = os.urandom(24) # Ustaw losowy klucz sesji

# Konfiguracja CORS: Zezwól na żądania z konkretnej domeny dla tras zaczynających się od /api/
CORS(app, resources={r"/api/*": {"origins": "https://jurek362.github.io"}})

# Prosta "baza danych" w pamięci
# Zmieniona struktura: {user_id: {"nickname": "...", "messages":}}
users = {}
user_ids = {} # {nickname: user_id}

# Usunięto trasy /login, /register (formularzowe), /logout, /check_login_status
# Aplikacja działa bez logowania/hasła, użytkownicy są tworzeni przez API

@app.route('/')
def index():
    """
    Główna strona aplikacji. Po prostu renderuje index.html.
    Nie ma już logiki sesji/logowania na tej trasie.
    """
    return render_template('index.html')

# TRASA API do tworzenia użytkowników z frontendu (np. JavaScript)
@app.route('/api/create-user', methods=)
def api_create_user():
    """
    Endpoint API do tworzenia nowego użytkownika.
    Wymaga tylko pseudonimu. Generuje unikalne user_id.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Brak danych JSON w żądaniu"}), 400 # Bad Request

    nickname = data.get('username') # Frontend wysyła 'username'

    if not nickname:
        return jsonify({"error": "Pseudonim jest wymagany"}), 400

    if nickname in user_ids:
        return jsonify({"error": "Nazwa użytkownika już zajęta"}), 409 # Conflict

    user_id = str(uuid.uuid4())
    users[user_id] = {
        "nickname": nickname,
        "messages": # Inicjalizuj pustą listę na wiadomości
    }
    user_ids[nickname] = user_id

    # Zwracamy odpowiedź JSON
    return jsonify({
        "success": True, # Dodano dla spójności z frontendem
        "message": "Użytkownik zarejestrowany pomyślnie",
        "user_id": user_id,
        "nickname": nickname
    }), 201 # Created

@app.route('/api/user/<string:nickname>', methods=)
def api_user_exists(nickname):
    """
    Endpoint API do sprawdzania, czy użytkownik o danym pseudonimie istnieje.
    Używany przez send_message.html do weryfikacji odbiorcy.
    """
    if nickname in user_ids:
        return jsonify({"exists": True, "user_id": user_ids[nickname], "nickname": nickname}), 200
    return jsonify({"exists": False, "error": "Użytkownik nie istnieje"}), 404

@app.route('/api/send-message', methods=)
def api_send_message():
    """
    Endpoint API do odbierania anonimowych wiadomości.
    Wiadomość jest przypisywana do pseudonimu odbiorcy.
    """
    data = request.get_json()
    target_nickname = data.get('username') # Frontend wysyła 'username'
    message_content = data.get('message')

    if not target_nickname or not message_content:
        return jsonify({"success": False, "error": "Pseudonim odbiorcy i wiadomość są wymagane"}), 400

    if target_nickname not in user_ids:
        return jsonify({"success": False, "error": "Użytkownik nie istnieje"}), 404

    target_user_id = user_ids[target_nickname]
    users[target_user_id]['messages'].append(message_content) # Dodaj wiadomość do listy odbiorcy

    return jsonify({"success": True, "message": "Wiadomość wysłana pomyślnie"}), 200

@app.route('/api/messages/<string:user_id>', methods=)
def api_get_messages(user_id):
    """
    Endpoint API do pobierania wszystkich wiadomości dla danego user_id.
    Używany przez dashboard.html.
    """
    if user_id not in users:
        return jsonify({"error": "Użytkownik nie istnieje"}), 404
    return jsonify({"messages": users[user_id]['messages'], "nickname": users[user_id]['nickname']}), 200


if __name__ == '__main__':
    app.run(debug=True)
