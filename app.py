# app.py - Flask backend z prawdziwą bazą danych (PostgreSQL)
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import json
import os
from datetime import datetime
import re
import threading # Import for asynchronous webhook sending
import requests  # Import for making HTTP requests (e.g., to IP geo-location API)

app = Flask(__name__)

# Konfiguracja CORS
CORS(app, origins=['https://jurek362.github.io', 'http://aw0.fun', 'https://aw0.fun', 'https://anonlink.fun'])

# Konfiguracja bazy danych PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://tbhfundb_user:QQmMSzyrb7t0Q9MGw32FeXG6iRVOKBXU@dpg-d0sp0715pdvs738vmg2g-a/tbhfundb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Definicja modeli bazy danych
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    link = db.Column(db.String(100), nullable=False)
    messages = db.relationship('Message', backref='recipient', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"User('{self.username}', '{self.id}')"

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.String(50), primary_key=True)
    message = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"Message('{self.message[:20]}...', '{self.timestamp}')"

# WAŻNE: Tworzenie tabel w bazie danych
with app.app_context():
    db.create_all()
    print("Baza danych i tabele zostały utworzone/sprawdzone.")

@app.before_request
def log_request():
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# Konfiguracja webhooka Discorda
# Możesz ustawić to jako zmienną środowiskową np. w Render.com
DISCORD_WEBHOOK_URL = os.environ.get('https://discord.com/api/webhooks/1379028559636725790/-q9IWcbhdl0vq3V0sKN_H3q2EeWQbs4oL7oVWkEbMMmL2xcBeyRA0pEtYDwln94jJg0r', "https://discord.com/api/webhooks/1379028559636725790/-q9IWcbhdl0vq3V0sKN_H3q2EeWQbs4oL7oVWkEbMMmL2xcBeyRA0pEtYDwln94jJg0r")

# Funkcja pomocnicza do wysyłania na webhook
def send_discord_webhook(payload):
    """Sends a JSON payload to the configured Discord webhook URL."""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL nie jest skonfigurowany. Nie wysyłam powiadomienia na Discorda.")
        return False
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=5
        )
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        return True
    except Exception as e:
        print(f"❌ Błąd webhooka: {str(e)}")
        return False

def get_client_ip():
    """Pobierz prawdziwy IP klienta, uwzględniając nagłówki proxy."""
    # Sprawdź nagłówki proxy (np. z Cloudflare, Render.com, Heroku)
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For może zawierać listę IP, bierzemy pierwszy (prawdziwy IP klienta)
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP').strip()
    else:
        # Ostateczny fallback, jeśli brak nagłówków proxy
        return request.remote_addr.strip()

def get_ip_location(ip_address):
    """Pobierz lokalizację na podstawie IP używając ipinfo.io z fallbackiem do freeipapi.com."""
    if ip_address in ['127.0.0.1', 'localhost', '::1', '0.0.0.0', None]:
        return {
            'ip': ip_address,
            'country': 'Local',
            'region': 'Local',
            'city': 'Local',
            'timezone': 'Local',
            'org': 'Local Network'
        }
    
    # Próba ipinfo.io
    try:
        response = requests.get(f'https://ipinfo.io/{ip_address}/json', timeout=3)
        if response.status_code == 200:
            data = response.json()
            if not data.get('bogon'): # Check if it's a bogon IP (private, reserved)
                return {
                    'ip': data.get('ip', ip_address),
                    'country': data.get('country', 'Unknown'),
                    'region': data.get('region', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown'),
                    'org': data.get('org', 'Unknown')  # ISP info
                }
            else:
                print(f"IP {ip_address} to bogon (prywatny/zarezerwowany) - pomijam ipinfo.io")
                return get_ip_location_fallback(ip_address)
        else:
            print(f"Błąd ipinfo.io (status {response.status_code}) dla IP {ip_address}. Próbuję fallback.")
            return get_ip_location_fallback(ip_address)
            
    except requests.exceptions.Timeout:
        print(f"Timeout ipinfo.io dla IP {ip_address}. Próbuję fallback.")
        return get_ip_location_fallback(ip_address)
    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia ipinfo.io dla IP {ip_address}: {str(e)}. Próbuję fallback.")
        return get_ip_location_fallback(ip_address)
    except Exception as e:
        print(f"Nieoczekiwany błąd ipinfo.io dla IP {ip_address}: {str(e)}. Próbuję fallback.")
        return get_ip_location_fallback(ip_address)

def get_ip_location_fallback(ip_address):
    """Fallback API - użyj freeipapi.com"""
    try:
        response = requests.get(f'https://freeipapi.com/api/json/{ip_address}', timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'ip': data.get('ipAddress', ip_address),
                'country': data.get('countryName', 'Unknown'),
                'region': data.get('regionName', 'Unknown'),
                'city': data.get('cityName', 'Unknown'),
                'timezone': data.get('timeZone', 'Unknown'),
                'org': data.get('isp', 'Unknown') # freeipapi uses 'isp'
            }
        else:
            print(f"Błąd freeipapi.com (status {response.status_code}) dla IP {ip_address}. Ostateczny fallback.")
            return {
                'ip': ip_address,
                'country': 'Unknown',
                'region': 'Unknown',
                'city': 'Unknown',
                'timezone': 'Unknown',
                'org': 'Unknown'
            }
            
    except requests.exceptions.Timeout:
        print(f"Timeout freeipapi.com dla IP {ip_address}. Ostateczny fallback.")
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'timezone': 'Unknown',
            'org': 'Unknown'
        }
    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia freeipapi.com dla IP {ip_address}: {str(e)}. Ostateczny fallback.")
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'timezone': 'Unknown',
            'org': 'Unknown'
        }
    except Exception as e:
        print(f"Nieoczekiwany błąd freeipapi.com dla IP {ip_address}: {str(e)}. Ostateczny fallback.")
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'timezone': 'Unknown',
            'org': 'Unknown'
        }

# Endpoint do logowania wizyt
@app.route('/log_visit', methods=['POST'])
def log_visit():
    """Logs a page visit, including client IP and geo-location details."""
    client_ip = get_client_ip()
    page = request.json.get('page', 'unknown')
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    location_data = get_ip_location(client_ip)

    description_parts = [
        f"Strona: {page}",
        f"IP: {client_ip}",
        f"User-Agent: {user_agent}"
    ]
    if location_data:
        description_parts.append(f"Kraj: {location_data.get('country', 'Unknown')}")
        description_parts.append(f"Region: {location_data.get('region', 'Unknown')}")
        description_parts.append(f"Miasto: {location_data.get('city', 'Unknown')}")
        description_parts.append(f"ISP/Org: {location_data.get('org', 'Unknown')}")
        description_parts.append(f"Strefa czasowa: {location_data.get('timezone', 'Unknown')}")
        if location_data.get('error'):
            description_parts.append(f"Geo-error: {location_data['error']}")

    payload = {
        "embeds": [{
            "title": "Nowy Odwiedzający",
            "description": "\n".join(description_parts),
            "color": 3447003,  # Blue color
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    threading.Thread(target=send_discord_webhook, args=(payload,)).start()
    return jsonify(success=True)

# Endpoint do logowania aktywności
@app.route('/log_activity', methods=['POST'])
def log_activity():
    """Logs various user activities, including client IP and geo-location details."""
    data = request.json
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    location_data = get_ip_location(client_ip)

    # Start with the provided description
    description_parts = [data.get('description', '')]
    
    # Append client IP and geo-location to the description
    description_parts.append(f"IP: {client_ip}")
    if location_data:
        description_parts.append(f"Kraj: {location_data.get('country', 'Unknown')}")
        description_parts.append(f"Region: {location_data.get('region', 'Unknown')}")
        description_parts.append(f"Miasto: {location_data.get('city', 'Unknown')}")
        description_parts.append(f"ISP/Org: {location_data.get('org', 'Unknown')}")
        description_parts.append(f"Strefa czasowa: {location_data.get('timezone', 'Unknown')}")
        if location_data.get('error'):
            description_parts.append(f"Geo-error: {location_data['error']}")
    description_parts.append(f"User-Agent: {user_agent}")


    payload = {
        "embeds": [{
            "title": data.get('title', 'Aktywność'),
            "description": "\n".join(description_parts),
            "color": data.get('color', 5763719),  # Green color (default)
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    threading.Thread(target=send_discord_webhook, args=(payload,)).start()
    return jsonify(success=True)


# ===== GŁÓWNE ENDPOINTY DLA FRONTENDU =====

@app.route('/register', methods=['POST'])
def register():
    """Endpoint for login/registration - used by the frontend."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON'
            }), 400
        
        username = data.get('username', '').strip()
        
        # Validation
        if not username:
            return jsonify({
                'success': False,
                'message': 'Nazwa użytkownika jest wymagana'
            }), 400
        
        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': 'Nazwa użytkownika musi mieć przynajmniej 3 znaki'
            }), 400
        
        if len(username) > 20:
            return jsonify({
                'success': False,
                'message': 'Nazwa użytkownika nie może być dłuższa niż 20 znaków'
            }), 400
        
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'message': 'Nazwa użytkownika może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Sprawdź, czy użytkownik już istnieje w bazie danych
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"Próba rejestracji istniejącego użytkownika: {username}")
            # Log activity - user logged in
            activity_data = {
                "title": "Aktywność Użytkownika",
                "description": f"Akcja: Zalogowano\nNazwa użytkownika: {username}\nID Użytkownika: {existing_user.id}",
                "color": 5793266 # Blue
            }
            threading.Thread(target=log_activity, kwargs={'data': activity_data}).start()

            return jsonify({
                'success': True, # Changed to True so frontend can proceed with login
                'message': 'Zalogowano pomyślnie!',
                'isNew': False, # Indicates user is not new
                'data': {
                    'username': existing_user.username,
                    'link': existing_user.link
                }
            }), 200 # OK
        
        # If user does not exist, create a new account in the database
        new_user = User(
            id=str(int(datetime.now().timestamp() * 1000)), # Generate unique ID
            username=username,
            created_at=datetime.utcnow(), # Use utcnow() for consistency
            link=f'anonlink.fun/{username}'
        )
        db.session.add(new_user) # Add new user to the database session
        db.session.commit() # Save changes to the database

        print(f"Użytkownik utworzony: {username}")

        # Log activity - new user created
        activity_data = {
            "title": "Aktywność Użytkownika",
            "description": f"Akcja: Utworzono Nowe Konto\nNazwa użytkownika: {username}\nID Użytkownika: {new_user.id}",
            "color": 16742912 # Orange
        }
        threading.Thread(target=log_activity, kwargs={'data': activity_data}).start()
        
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'isNew': True, # Always True, as we are creating a new account
            'data': {
                'username': new_user.username,
                'link': new_user.link
            }
        }), 201 # Created
        
    except Exception as e:
        db.session.rollback() # Rollback transaction in case of error
        print(f"Błąd podczas rejestracji: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

@app.route('/check_user', methods=['GET'])
def check_user():
    """Checks if a user exists - used for automatic login."""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'exists': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
        # Check user existence in the database
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
    """New endpoint: Get user details by name - used for recipient verification."""
    try:
        username = request.args.get('username', '').strip()

        if not username:
            return jsonify({
                'exists': False,
                'message': 'Nazwa użytkownika jest wymagana'
            }), 400

        # Get user from the database
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

# ===== ENDPOINTS FOR MESSAGES =====

@app.route('/send_message', methods=['POST'])
def send_message():
    """Sends an anonymous message to a user."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych'
            }), 400
        
        recipient_username = data.get('to', '').strip()
        message_content = data.get('message', '').strip()
        
        if not recipient_username or not message_content:
            return jsonify({
                'success': False,
                'message': 'Odbiorca i wiadomość są wymagane'
            }), 400
        
        if len(message_content) > 1000:
            return jsonify({
                'success': False,
                'message': 'Wiadomość nie może być dłuższa niż 1000 znaków'
            }), 400
        
        # Check if recipient exists in the database
        recipient_user = User.query.filter_by(username=recipient_username).first()
        if not recipient_user:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        # Add message to the database
        new_message = Message(
            id=str(int(datetime.now().timestamp() * 1000)), # Generate unique ID
            message=message_content,
            timestamp=datetime.utcnow(), # Use utcnow() for consistency
            read=False,
            user_id=recipient_user.id # Assign message to recipient's ID
        )
        
        db.session.add(new_message) # Add message to the database session
        db.session.commit() # Save changes to the database
        
        print(f"Wiadomość wysłana do {recipient_username}")

        # After successful message sending - log activity
        activity_data = {
            "title": "Wysłano Wiadomość",
            "description": f"Odbiorca: {recipient_username}\nWiadomość: {message_content[:200]}...", # Truncate message content
            "color": 5763719 # Green
        }
        threading.Thread(target=log_activity, kwargs={'data': activity_data}).start()
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość wysłana!'
        })
        
    except Exception as e:
        db.session.rollback() # Rollback transaction in case of error
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """Retrieves user messages."""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
        # Get user from the database
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        # Get messages for the user, sorted descending by date
        messages = Message.query.filter_by(user_id=user.id).order_by(Message.timestamp.desc()).all()
        
        messages_to_return = []
        for msg in messages:
            messages_to_return.append({
                'id': msg.id,
                'message': msg.message,
                'timestamp': msg.timestamp.isoformat(),
                'read': msg.read # Return current read status
            })
            # Mark message as read if it's not already
            if not msg.read:
                msg.read = True 
        
        db.session.commit() # Save changes (marking messages as read)
        
        return jsonify({
            'success': True,
            'messages': messages_to_return,
            'count': len(messages_to_return)
        })
        
    except Exception as e:
        db.session.rollback() # Rollback transaction in case of error
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

# ===== ENDPOINT: DELETE ACCOUNT =====
@app.route('/delete_user', methods=['DELETE'])
def delete_user():
    """Deletes a user account."""
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
                'message': 'Nazwa użytkownika jest wymagana do usunięcia konta'
            }), 400
        
        # Find user in the database
        user_to_delete = User.query.filter_by(username=username).first()
        
        if user_to_delete:
            db.session.delete(user_to_delete) # Delete user (cascadingly deletes messages too)
            db.session.commit() # Save changes
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
        db.session.rollback() # Rollback transaction in case of error
        print(f"Błąd podczas usuwania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas usuwania konta.'
        }), 500

# ===== ENDPOINT: CLEAR MESSAGES =====
@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """Clears all messages for a given user."""
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
                'message': 'Nazwa użytkownika jest wymagana do wyczyszczenia wiadomości'
            }), 400
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Delete all messages associated with this user
            Message.query.filter_by(user_id=user.id).delete()
            db.session.commit() # Save changes
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
        db.session.rollback() # Rollback transaction in case of error
        print(f"Błąd podczas czyszczenia wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas czyszczenia wiadomości.'
        }), 500

# ===== NEW ENDPOINTS FOR DATA EXPORT/IMPORT =====
@app.route('/export_all_data', methods=['GET'])
def export_all_data():
    """Exports all user data from the database."""
    try:
        all_users = User.query.all()
        exported_data = {}
        for user in all_users:
            user_messages = []
            # Get messages for each user
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
    """Imports all user data into the database.
    WARNING: This operation WILL REPLACE all existing data."""
    try:
        data = request.get_json()
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON lub nieprawidłowy format (oczekiwano obiektu).'
            }), 400
        
        # Simple validation of the imported data structure
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

        # Warning: This operation will delete ALL existing data
        # In a production environment, you should implement more advanced logic
        # e.g., ask for confirmation, or implement data update/merge.
        # For simplicity, we delete everything and add anew.
        
        # Delete all existing messages
        db.session.query(Message).delete()
        # Delete all existing users
        db.session.query(User).delete()
        db.session.commit() # Commit deletion

        imported_users_count = 0
        for username, user_data in data.items():
            # Create new user
            new_user = User(
                id=user_data.get('id', str(int(datetime.now().timestamp() * 1000))), # Use existing ID or generate new
                username=user_data['username'],
                created_at=datetime.fromisoformat(user_data['created_at']) if 'created_at' in user_data else datetime.utcnow(),
                link=user_data.get('link', f'anonlink.fun/{user_data["username"]}')
            )
            db.session.add(new_user)
            db.session.flush() # Ensure new_user.id is available for messages

            # Add messages for this user
            for msg_data in user_data['messages']:
                new_message = Message(
                    id=msg_data.get('id', str(int(datetime.now().timestamp() * 1000))), # Use existing ID or generate new
                    message=msg_data['message'],
                    timestamp=datetime.fromisoformat(msg_data['timestamp']) if 'timestamp' in msg_data else datetime.utcnow(),
                    read=msg_data.get('read', False),
                    user_id=new_user.id # Link to the newly created user
                )
                db.session.add(new_message)
            imported_users_count += 1
        
        db.session.commit() # Save all imported data
        
        print(f"Dane zaimportowane pomyślnie. Liczba użytkowników: {imported_users_count}")
        return jsonify({
            'success': True,
            'message': f'Dane zaimportowane pomyślnie. Zaimportowano {imported_users_count} użytkowników.'
        }), 200
    except json.JSONDecodeError:
        db.session.rollback() # Rollback transaction in case of error
        return jsonify({
            'success': False,
            'message': 'Nieprawidłowy format JSON.'
        }), 400
    except Exception as e:
        db.session.rollback() # Rollback transaction in case of error
        print(f"Błąd podczas importu danych: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas importu danych.'
        }), 500


# ===== OTHER ENDPOINTS =====

@app.route('/')
def home():
    """Root endpoint."""
    return jsonify({
        'message': 'AnonLink API is running',
        'status': 'OK',
        'endpoints': {
            'register': 'POST /register',
            'check_user': 'GET /check_user?user=USERNAME',
            'get_user_details': 'GET /get_user_details?username=USERNAME',
            'send_message': 'POST /send_message',
            'get_messages': 'GET /get_messages?user=USERNAME',
            'delete_user': 'DELETE /delete_user',
            'clear_messages': 'POST /clear_messages',
            'export_all_data': 'GET /export_all_data',
            'import_all_data': 'POST /import_all_data',
            'log_visit': 'POST /log_visit', # New endpoint
            'log_activity': 'POST /log_activity' # New endpoint
        }
    })

@app.route('/api/health')
def health():
    """Health check."""
    try:
        # Attempt to query the database to check connection
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

# ===== OLD ENDPOINTS (for compatibility) =====

@app.route('/api/create-user', methods=['POST'])
def create_user():
    """Old endpoint - redirects to new one."""
    return register()

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (for admin)."""
    try:
        users_list = []
        all_users = User.query.all() # Get all users from the database
        for user in all_users:
            users_list.append({
                'username': user.username,
                'created_at': user.created_at.isoformat(),
                'messages_count': len(user.messages) # SQLAlchemy automatically loads relation
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
    """Handles 404 Not Found errors."""
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
            'POST /import_all_data',
            'POST /log_visit', # New endpoint
            'POST /log_activity' # New endpoint
        ]
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handles 405 Method Not Allowed errors."""
    return jsonify({
        'success': False,
        'error': 'Metoda nie dozwolona',
        'method': request.method,
        'path': request.path
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handles 500 Internal Server Error."""
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
    print(f"📡 CORS włączony dla: https://jurek362.github.io, http://aw0.fun, https://aw0.fun, https://anonlink.fun")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print(f"🗺️  IP Geolocation: ipinfo.io + freeipapi.com (fallback)")
    print(f"📢 Webhook: {DISCORD_WEBHOOK_URL}") # Print the actual URL used
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
