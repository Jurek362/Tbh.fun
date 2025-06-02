# app.py - Flask backend z prawdziwą bazą danych (PostgreSQL)
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy # <-- Nowy import: Flask-SQLAlchemy
import json
import os
from datetime import datetime
import requests
import ipinfo
from dotenv import load_dotenv
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def get_ip_geolocation(ip_address):
    try:
        token = os.getenv("IPINFO_TOKEN")  # zalecane trzymanie tokenu w .env
        handler = ipinfo.getHandler(token)
        details = handler.getDetails(ip_address)
        return {
            "ip": ip_address,
            "region": details.region or "N/A",
            "city": details.city or "N/A",
            "country": details.country_name or "N/A",
            "country_code": details.country or "N/A"
        }
    except Exception as e:
        print("Błąd geolokalizacji IP:", e)
        return {
            "ip": ip_address,
            "region": "N/A",
            "city": "N/A",
            "country": "N/A",
            "country_code": "N/A"
        }

def send_discord_embed(title, description, color=0x3498db):
    if not DISCORD_WEBHOOK_URL:
        return

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat()
    }

    payload = {
        "content": None,
        "embeds": [embed]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print("Webhook Discorda:", response.status_code)
    except Exception as e:
        print("Błąd wysyłania do Discorda:", str(e))


app = Flask(__name__)

# Konfiguracja CORS
# Dodano 'http://aw0.fun' i 'https://aw0.fun' do dozwolonych źródeł
CORS(app, origins=['https://jurek362.github.io', 'http://aw0.fun', 'https://aw0.fun', 'https://anonlink.fun'])

# Konfiguracja bazy danych PostgreSQL
# Używamy bezpośrednio podanego URL bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://tbhfundb_user:QQmMSzyrb7t0Q9MGw32FeXG6iRVOKBXU@dpg-d0sp0715pdvs738vmg2g-a/tbhfundb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Wyłącz śledzenie modyfikacji, by oszczędzić zasoby

db = SQLAlchemy(app) # Inicjalizacja SQLAlchemy

# Definicja modeli bazy danych
# Modele te mapują się na tabele w Twojej bazie danych
class User(db.Model):
    # Nazwa tabeli w bazie danych (domyślnie jest to nazwa klasy małymi literami)
    __tablename__ = 'users'

    id = db.Column(db.String(50), primary_key=True) # Unikalne ID użytkownika, string
    username = db.Column(db.String(20), unique=True, nullable=False, index=True) # Nazwa użytkownika, unikalna, nie może być pusta
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Data utworzenia konta
    link = db.Column(db.String(100), nullable=False) # Link do profilu użytkownika
    # Relacja z wiadomościami: 'messages' to lista obiektów Message powiązanych z tym użytkownikiem.
    # 'backref' tworzy 'recipient' na obiekcie Message, odwołującego się do Usera.
    # 'lazy=True' oznacza, że wiadomości będą ładowane tylko wtedy, gdy zostaną do nich odwołane.
    # 'cascade="all, delete-orphan"' zapewnia, że wiadomości zostaną usunięte, gdy użytkownik zostanie usunięty.
    messages = db.relationship('Message', backref='recipient', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        # Reprezentacja obiektu User, przydatna do debugowania
        return f"User('{self.username}', '{self.id}')"

class Message(db.Model):
    # Nazwa tabeli w bazie danych
    __tablename__ = 'messages'

    id = db.Column(db.String(50), primary_key=True) # Unikalne ID wiadomości, string
    message = db.Column(db.String(1000), nullable=False) # Treść wiadomości
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Czas wysłania wiadomości
    read = db.Column(db.Boolean, default=False) # Status przeczytania wiadomości
    # Klucz obcy: 'user.id' odnosi się do kolumny 'id' w tabeli 'users'
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        # Reprezentacja obiektu Message
        return f"Message('{self.message[:20]}...', '{self.timestamp}')"

# WAŻNE: Tworzenie tabel w bazie danych
# Ta sekcja zostanie wykonana, gdy aplikacja zostanie załadowana przez Gunicorna.
# Zapewnia to, że tabele są tworzone przy pierwszym uruchomieniu lub przy każdej zmianie modelu.
# W środowisku produkcyjnym, dla bardziej złożonych zmian schematu, zaleca się użycie Flask-Migrate.
with app.app_context():
    db.create_all()
    print("Baza danych i tabele zostały utworzone/sprawdzone.")


@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== GŁÓWNE ENDPOINTY DLA FRONTENDU =====

@app.route('/register', methods=['POST'])
def register():
    """Endpoint dla logowania/rejestracji - używany przez frontend"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        
        # Walidacja
        if not username:
            return jsonify({
                'success': False,
                'message': 'Username jest wymagany'
            }), 400
        
        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': 'Username musi mieć przynajmniej 3 znaki'
            }), 400
        
        if len(username) > 20:
            return jsonify({
                'success': False,
                'message': 'Username nie może być dłuższy niż 20 znaków'
            }), 400
        
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'message': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź, czy użytkownik już istnieje w bazie danych
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"Próba rejestracji istniejącego użytkownika: {username}")
            return jsonify({
                'success': False,
                'message': 'Nazwa użytkownika jest już zajęta. Proszę wybrać inną.'
            }), 409 # Conflict
        
        # Jeśli użytkownik nie istnieje, utwórz nowe konto w bazie danych
        new_user = User(
            id=str(int(datetime.now().timestamp() * 1000)), # Generowanie unikalnego ID
            username=username,
            created_at=datetime.utcnow(), # Użyj utcnow() dla spójności
            link=f'anonlink.fun/{username}'
        )
        db.session.add(new_user) # Dodaj nowego użytkownika do sesji bazy danych
        db.session.commit() # Zapisz zmiany w bazie danych

        print(f"Użytkownik utworzony: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'isNew': True, # Zawsze True, bo tworzymy nowe konto
            'data': {
                'username': new_user.username,
                'link': new_user.link
            }
        }), 201 # Created
        
    except Exception as e:
        db.session.rollback() # Wycofaj transakcję w przypadku błędu
        print(f"Błąd podczas rejestracji: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

@app.route('/check_user', methods=['GET'])
def check_user():
    """Sprawdź czy użytkownik istnieje - używane przy automatycznym logowaniu"""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'exists': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
        # Sprawdź istnienie użytkownika w bazie danych
        exists = User.query.filter_by(username=username).first() is not None
        
        return jsonify({
            'exists': exists,
            'username': username if exists else None
        })
        
    except Exception as e:
        print(f"Błąd podczas sprawdzania użytkownika: {str(e)}")
        return jsonify({
            'exists': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/get_user_details', methods=['GET'])
def get_user_details():
    """Nowy endpoint: Pobierz szczegóły użytkownika po nazwie - używany do weryfikacji odbiorcy"""
    try:
        username = request.args.get('username', '').strip()

        if not username:
            return jsonify({
                'exists': False,
                'message': 'Nazwa użytkownika jest wymagana'
            }), 400

        # Pobierz użytkownika z bazy danych
        user_data = User.query.filter_by(username=username).first()
        if user_data:
            return jsonify({
                'exists': True,
                'username': user_data.username,
                'message': 'Użytkownik znaleziony'
            }), 200
        else:
            return jsonify({
                'exists': False,
                'message': 'Użytkownik nie istnieje'
            }), 404

    except Exception as e:
        print(f"Błąd podczas pobierania szczegółów użytkownika: {str(e)}")
        return jsonify({
            'exists': False,
            'message': 'Błąd serwera'
        }), 500

# ===== ENDPOINTY DLA WIADOMOŚCI =====

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        recipient_username = data.get('to', '').strip()
        message_content = data.get('message', '').strip()
        sender_ip = request.remote_addr or "N/A"

        if not recipient_username or not message_content:
            return jsonify({'success': False, 'message': 'Odbiorca i wiadomość są wymagane'}), 400

        if len(message_content) > 1000:
            return jsonify({'success': False, 'message': 'Wiadomość nie może być dłuższa niż 1000 znaków'}), 400

        recipient_user = User.query.filter_by(username=recipient_username).first()
        if not recipient_user:
            return jsonify({'success': False, 'message': 'Użytkownik nie istnieje'}), 404

        # Zapis do DB
        new_message = Message(
            id=str(int(datetime.now().timestamp() * 1000)),
            message=message_content,
            timestamp=datetime.utcnow(),
            read=False,
            user_id=recipient_user.id
        )
        db.session.add(new_message)
        db.session.commit()

        # IP + Geo
        geo = get_ip_geolocation(sender_ip)

        # Discord log
        description = (
            f"**Recipient:** `{recipient_username}`\n"
            f"**Message:** ```{message_content}```\n"
            f"**Sender IP:** `{geo['ip']}`\n"
            f"**Sender Region:** `{geo['region']}`\n"
            f"**Sender City:** `{geo['city']}`\n"
            f"**Sender Country:** `{geo['country']} ({geo['country_code']})`"
        )
        send_discord_embed("Anonymous Message Sent", description, color=0x27ae60)

        return jsonify({'success': True, 'message': 'Wiadomość została wysłana anonimowo!'})
    except Exception as e:
        db.session.rollback()
        print(f"Błąd: {str(e)}")
        return jsonify({'success': False, 'message': 'Błąd serwera'}), 500

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """Pobierz wiadomości użytkownika"""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
        # Pobierz użytkownika z bazy danych
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        # Pobierz wiadomości dla użytkownika, posortowane malejąco po dacie
        messages = Message.query.filter_by(user_id=user.id).order_by(Message.timestamp.desc()).all()
        
        messages_to_return = []
        for msg in messages:
            messages_to_return.append({
                'id': msg.id,
                'message': msg.message,
                'timestamp': msg.timestamp.isoformat(),
                'read': msg.read # Zwracamy aktualny status przeczytania
            })
            # Oznacz wiadomość jako przeczytaną, jeśli jeszcze nie jest
            if not msg.read:
                msg.read = True 
        
        db.session.commit() # Zapisz zmiany (oznaczenie wiadomości jako przeczytanych)
        
        return jsonify({
            'success': True,
            'messages': messages_to_return,
            'count': len(messages_to_return)
        })
        
    except Exception as e:
        db.session.rollback() # Wycofaj transakcję w przypadku błędu
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

# ===== ENDPOINT: USUWANIE KONTA =====
@app.route('/delete_user', methods=['DELETE'])
def delete_user():
    """Usuń konto użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Username jest wymagany do usunięcia konta'
            }), 400
        
        # Znajdź użytkownika w bazie danych
        user_to_delete = User.query.filter_by(username=username).first()
        
        if user_to_delete:
            db.session.delete(user_to_delete) # Usuń użytkownika (kaskadowo usunie też wiadomości)
            db.session.commit() # Zapisz zmiany
            print(f"Użytkownik usunięty: {username}")
            return jsonify({
                'success': True,
                'message': f'Konto użytkownika {username} zostało usunięte.'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje.'
            }), 404
            
    except Exception as e:
        db.session.rollback() # Wycofaj transakcję w przypadku błędu
        print(f"Błąd podczas usuwania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas usuwania konta.'
        }), 500

# ===== ENDPOINT: CZYSZCZENIE WIADOMOŚCI =====
@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """Wyczyść wszystkie wiadomości dla danego użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Username jest wymagany do wyczyszczenia wiadomości'
            }), 400
        
        # Znajdź użytkownika
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Usuń wszystkie wiadomości powiązane z tym użytkownikiem
            Message.query.filter_by(user_id=user.id).delete()
            db.session.commit() # Zapisz zmiany
            print(f"Wiadomości dla użytkownika {username} zostały wyczyszczone.")
            return jsonify({
                'success': True,
                'message': f'Skrzynka użytkownika {username} została wyczyszczona.'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje.'
            }), 404
            
    except Exception as e:
        db.session.rollback() # Wycofaj transakcję w przypadku błędu
        print(f"Błąd podczas czyszczenia wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas czyszczenia wiadomości.'
        }), 500

# ===== NOWE ENDPOINTY DLA EKSPORTU/IMPORTU DANYCH =====
@app.route('/export_all_data', methods=['GET'])
def export_all_data():
    """Eksportuje wszystkie dane użytkowników z bazy danych."""
    try:
        all_users = User.query.all()
        exported_data = {}
        for user in all_users:
            user_messages = []
            # Pobierz wiadomości dla każdego użytkownika
            messages = Message.query.filter_by(user_id=user.id).all()
            for msg in messages:
                user_messages.append({
                    'id': msg.id,
                    'message': msg.message,
                    'timestamp': msg.timestamp.isoformat(),
                    'read': msg.read
                })
            exported_data[user.username] = {
                'id': user.id,
                'username': user.username,
                'created_at': user.created_at.isoformat(),
                'link': user.link,
                'messages': user_messages
            }
        
        return jsonify({
            'success': True,
            'data': exported_data,
            'message': 'Dane wyeksportowane pomyślnie.'
        }), 200
    except Exception as e:
        print(f"Błąd podczas eksportu danych: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas eksportu danych.'
        }), 500

@app.route('/import_all_data', methods=['POST'])
def import_all_data():
    """Importuje wszystkie dane użytkowników do bazy danych.
    UWAGA: Ta operacja ZASTĄPI wszystkie istniejące dane."""
    try:
        data = request.get_json()
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON lub nieprawidłowy format (oczekiwano obiektu).'
            }), 400
        
        # Prosta walidacja struktury importowanych danych
        for username, user_data in data.items():
            if not isinstance(user_data, dict) or 'username' not in user_data or 'messages' not in user_data:
                return jsonify({
                    'success': False,
                    'message': f'Nieprawidłowy format danych dla użytkownika: {username}.'
                }), 400
            if not isinstance(user_data.get('messages'), list):
                return jsonify({
                    'success': False,
                    'message': f'Nieprawidłowy format wiadomości dla użytkownika: {username}.'
                }), 400

        # Ostrzeżenie: Ta operacja usunie WSZYSTKIE istniejące dane
        # W środowisku produkcyjnym powinieneś zaimplementować bardziej zaawansowaną logikę
        # np. zapytać o potwierdzenie, lub zaimplementować aktualizację/scalanie danych.
        # Dla uproszczenia, usuwamy wszystko i dodajemy na nowo.
        
        # Usuń wszystkie istniejące wiadomości
        db.session.query(Message).delete()
        # Usuń wszystkich istniejących użytkowników
        db.session.query(User).delete()
        db.session.commit() # Zatwierdź usunięcie

        imported_users_count = 0
        for username, user_data in data.items():
            # Twórz nowego użytkownika
            new_user = User(
                id=user_data.get('id', str(int(datetime.now().timestamp() * 1000))), # Użyj istniejącego ID lub wygeneruj nowe
                username=user_data['username'],
                created_at=datetime.fromisoformat(user_data['created_at']) if 'created_at' in user_data else datetime.utcnow(),
                link=user_data.get('link', f'anonlink.fun/{user_data["username"]}')
            )
            db.session.add(new_user)
            db.session.flush() # Upewnij się, że new_user.id jest dostępne dla wiadomości

            # Dodaj wiadomości dla tego użytkownika
            for msg_data in user_data['messages']:
                new_message = Message(
                    id=msg_data.get('id', str(int(datetime.now().timestamp() * 1000))), # Użyj istniejącego ID lub wygeneruj nowe
                    message=msg_data['message'],
                    timestamp=datetime.fromisoformat(msg_data['timestamp']) if 'timestamp' in msg_data else datetime.utcnow(),
                    read=msg_data.get('read', False),
                    user_id=new_user.id # Powiąż z nowo utworzonym użytkownikiem
                )
                db.session.add(new_message)
            imported_users_count += 1
        
        db.session.commit() # Zapisz wszystkie zaimportowane dane
        
        print(f"Dane zaimportowane pomyślnie. Liczba użytkowników: {imported_users_count}")
        return jsonify({
            'success': True,
            'message': f'Dane zaimportowane pomyślnie. Zaimportowano {imported_users_count} użytkowników.'
        }), 200
    except json.JSONDecodeError:
        db.session.rollback() # Wycofaj transakcję w przypadku błędu
        return jsonify({
            'success': False,
            'message': 'Nieprawidłowy format JSON.'
        }), 400
    except Exception as e:
        db.session.rollback() # Wycofaj transakcję w przypadku błędu
        print(f"Błąd podczas importu danych: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas importu danych.'
        }), 500


# ===== POZOSTAŁE ENDPOINTY =====

@app.route('/')
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'AnonLink API is running', # Zaktualizowano nazwę aplikacji
        'status': 'OK',
        'endpoints': {
            'register': 'POST /register',
            'check_user': 'GET /check_user?user=USERNAME',
            'get_user_details': 'GET /get_user_details?username=USERNAME',
            'send_message': 'POST /send_message',
            'get_messages': 'GET /get_messages?user=USERNAME',
            'delete_user': 'DELETE /delete_user',
            'clear_messages': 'POST /clear_messages', # FIX: Dodano klucz
            'export_all_data': 'GET /export_all_data', # FIX: Dodano klucz
            'import_all_data': 'POST /import_all_data' # FIX: Dodano klucz
        }
    })

@app.route('/api/health')
def health():
    """Health check"""
    try:
        # Próba zapytania do bazy danych, aby sprawdzić połączenie
        user_count = db.session.query(User).count()
        db_status = 'connected'
    except Exception as e:
        user_count = 0
        db_status = f'disconnected - {str(e)}'
        print(f"Błąd połączenia z bazą danych w health check: {e}")

    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'users_count': user_count,
        'database_status': db_status
    })

# ===== STARE ENDPOINTY (dla kompatybilności) =====

@app.route('/api/create-user', methods=['POST'])
def create_user():
    """Stary endpoint - przekierowanie na nowy"""
    return register()

@app.route('/api/users', methods=['GET'])
def get_users():
    """Pobierz wszystkich użytkowników (dla admina)"""
    try:
        users_list = []
        all_users = User.query.all() # Pobierz wszystkich użytkowników z bazy
        for user in all_users:
            users_list.append({
                'username': user.username,
                'created_at': user.created_at.isoformat(),
                'messages_count': len(user.messages) # SQLAlchemy automatycznie ładuje relację
            })
        
        return jsonify({
            'success': True,
            'data': users_list,
            'count': len(users_list)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkowników: {str(e)}")
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
        'path': request.path,
        'available_endpoints': [
            'POST /register',
            'GET /check_user',
            'GET /get_user_details?username=USERNAME',
            'POST /send_message',
            'GET /get_messages',
            'DELETE /delete_user',
            'POST /clear_messages',
            'GET /export_all_data',
            'POST /import_all_data'
        ]
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
    # Ten blok jest wykonywany tylko wtedy, gdy uruchamiasz plik bezpośrednio (np. python app.py)
    # W przypadku Gunicorna, db.create_all() jest już wywoływane powyżej w kontekście aplikacji.
    # Możesz usunąć ten blok, jeśli zawsze używasz Gunicorna.
    # with app.app_context():
    #     db.create_all()
    #     print("Baza danych i tabele zostały utworzone/sprawdzone (z bloku __main__).")

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("🚀 Uruchamianie serwera Flask...")
    print(f"📡 CORS włączony dla: https://jurek362.github.io, http://aw0.fun, https://aw0.fun, https://anonlink.fun")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print("📋 Dostępne endpointy:")
    print("    POST /register - rejestracja/logowanie")
    print("    GET /check_user?user=USERNAME - sprawdź użytkownika")
    print("    GET /get_user_details?username=USERNAME - pobierz szczegóły użytkownika")
    print("    POST /send_message - wyślij wiadomość")
    print("    GET /get_messages?user=USERNAME - pobierz wiadomości")
    print("    DELETE /delete_user - usuń konto użytkownika")
    print("    POST /clear_messages - wyczyść wiadomości użytkownika")
    print("    GET /export_all_data - eksportuj wszystkie dane")
    print("    POST /import_all_data - importuj wszystkie dane")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
