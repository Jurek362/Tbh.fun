# app.py - Flask backend z dodanymi endpointami dla frontendu i bazą danych PostgreSQL
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy
from flask_migrate import Migrate # Import Flask-Migrate
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

# CORS konfiguracja
CORS(app, origins=['https://jurek362.github.io'])

# ===== KONFIGURACJA BAZY DANYCH DLA RENDER (PostgreSQL) =====
# Render automatycznie dostarcza zmienną środowiskową DATABASE_URL dla baz danych PostgreSQL.
# Używamy os.environ.get() do pobrania tego URL.
# Dla lokalnego rozwoju możesz ustawić zmienną DATABASE_URL lub użyć domyślnego SQLite.
# Ważne: 'postgresql' w URI dla SQLAlchemy może wymagać 'postgresql+psycopg2'
# jeśli masz problemy z połączeniem, ale Render zazwyczaj to obsługuje.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tbhfun.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Wyłącz śledzenie modyfikacji, aby zużywać mniej pamięci

db = SQLAlchemy(app)
migrate = Migrate(app, db) # Inicjalizacja Flask-Migrate

# ===== MODELE BAZY DANYCH =====
class User(db.Model):
    __tablename__ = 'users' # Nazwa tabeli w bazie danych
    id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacja z wiadomościami. 'lazy=True' oznacza, że wiadomości będą ładowane tylko wtedy, gdy będą potrzebne.
    # 'cascade="all, delete-orphan"' zapewni usunięcie wiadomości, gdy użytkownik zostanie usunięty.
    messages = db.relationship('Message', backref='recipient_user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

class Message(db.Model):
    __tablename__ = 'messages' # Nazwa tabeli w bazie danych
    id = db.Column(db.String(50), primary_key=True)
    content = db.Column(db.String(1000), nullable=False) # Zmieniono 'message' na 'content' dla spójności z modelem
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    # Klucz obcy łączący wiadomość z użytkownikiem
    recipient_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"<Message {self.id} to {self.recipient_id}>"

# UWAGA: db.create_all() zostało usunięte z głównego bloku uruchamiania.
# Schemat bazy danych będzie zarządzany przez Flask-Migrate (Alembic).


@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== GŁÓWNE ENDPOINTY DLA FRONTENDU =====

@app.route('/register', methods=['POST'])
def register():
    """Endpoint for login/registration - used by frontend"""
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
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        
        if not existing_user:
            # Create new user
            new_user = User(
                id=str(int(datetime.now().timestamp() * 1000)),
                username=username,
                created_at=datetime.utcnow() # Use utcnow() for consistency
            )
            db.session.add(new_user)
            db.session.commit()
            is_new = True
        else:
            is_new = False
        
        print(f"Użytkownik {'zalogowany' if not is_new else 'utworzony'}: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Zalogowano pomyślnie!' if not is_new else 'Konto utworzone!',
            'isNew': is_new,
            'data': {
                'username': username,
                'link': f'tbh.fun/{username}'
            }
        }), 200
        
    except Exception as e:
        db.session.rollback() # Rollback in case of error
        print(f"Błąd podczas rejestracji: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

@app.route('/check_user', methods=['GET'])
def check_user():
    """Check if user exists - used for automatic login"""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'exists': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
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
    """New endpoint: Get user details by name - used for recipient verification"""
    try:
        username = request.args.get('username', '').strip()

        if not username:
            return jsonify({
                'exists': False,
                'message': 'Nazwa użytkownika jest wymagana'
            }), 400

        user = User.query.filter_by(username=username).first()

        if user:
            return jsonify({
                'exists': True,
                'username': user.username,
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
    """Send anonymous message to user"""
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
        
        # Check if recipient exists
        recipient_user = User.query.filter_by(username=recipient_username).first()
        if not recipient_user:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        # Add message
        new_message = Message(
            id=str(int(datetime.now().timestamp() * 1000)),
            content=message_content,
            timestamp=datetime.utcnow(),
            read=False,
            recipient_id=recipient_user.id # Link message to recipient user ID
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        print(f"Wiadomość wysłana do {recipient_username}")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość wysłana!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """Get user messages"""
    try:
        username = request.args.get('user', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Brak nazwy użytkownika'
            }), 400
        
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        # Get messages for the user, ordered by timestamp descending
        messages = Message.query.filter_by(recipient_id=user.id).order_by(Message.timestamp.desc()).all()
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'message': msg.content, # Frontend expects 'message'
                'timestamp': msg.timestamp.isoformat(),
                'read': msg.read # Keep 'read' status
            })
            # Mark message as read (optional, can be done on frontend or separate endpoint)
            if not msg.read:
                msg.read = True
                db.session.add(msg) # Add to session for update
        
        db.session.commit() # Commit changes to mark messages as read
        
        return jsonify({
            'success': True,
            'messages': messages_data,
            'count': len(messages_data)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Błąd podczas pobierania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

# ===== ENDPOINT: USUWANIE KONTA =====
@app.route('/delete_user', methods=['DELETE'])
def delete_user():
    """Delete user account"""
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
        
        user_to_delete = User.query.filter_by(username=username).first()
        
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()
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
        db.session.rollback()
        print(f"Błąd podczas usuwania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas usuwania konta.'
        }), 500

# ===== ENDPOINT: CZYSZCZENIE WIADOMOŚCI =====
@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """Clear all messages for a given user"""
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
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Delete all messages associated with this user
            Message.query.filter_by(recipient_id=user.id).delete()
            db.session.commit()
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
        db.session.rollback()
        print(f"Błąd podczas czyszczenia wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas czyszczenia wiadomości.'
        }), 500

# ===== POZOSTAŁE ENDPOINTY =====

@app.route('/')
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'endpoints': {
            'register': 'POST /register',
            'check_user': 'GET /check_user?user=USERNAME',
            'get_user_details': 'GET /get_user_details?username=USERNAME',
            'send_message': 'POST /send_message',
            'get_messages': 'GET /get_messages?user=USERNAME',
            'delete_user': 'DELETE /delete_user',
            'clear_messages': 'POST /clear_messages'
        }
    })

@app.route('/api/health')
def health():
    """Health check"""
    # Count users and messages from the database
    user_count = User.query.count()
    message_count = Message.query.count()
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'users_count': user_count,
        'messages_count': message_count # Added message count
    })

# ===== STARE ENDPOINTY (dla kompatybilności) =====

@app.route('/api/create-user', methods=['POST'])
def create_user():
    """Old endpoint - redirects to new one"""
    return register()

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (for admin)"""
    try:
        users_list = []
        # Query all users from the database
        all_users = User.query.all()
        for user in all_users:
            users_list.append({
                'username': user.username,
                'created_at': user.created_at.isoformat(),
                'messages_count': len(user.messages) # Access messages via relationship
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
            'POST /clear_messages'
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
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("🚀 Uruchamianie serwera Flask...")
    print(f"📡 CORS włączony dla: https://jurek362.github.io")
    print(f"🌍 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print("📋 Dostępne endpointy:")
    print("   POST /register - rejestracja/logowanie")
    print("   GET /check_user?user=USERNAME - sprawdź użytkownika")
    print("   GET /get_user_details?username=USERNAME - pobierz szczegóły użytkownika")
    print("   POST /send_message - wyślij wiadomość")
    print("   GET /get_messages?user=USERNAME - pobierz wiadomości")
    print("   DELETE /delete_user - usuń konto użytkownika")
    print("   POST /clear_messages - wyczyść wiadomości użytkownika")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

