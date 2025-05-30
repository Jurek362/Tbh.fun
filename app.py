# app.py - Flask backend z tymczasową bazą danych oraz endpointami dla eksportu/importu
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import re

app = Flask(__name__)

# CORS konfiguracja
CORS(app, origins=['https://jurek362.github.io'])

# Tymczasowa "baza danych" w pamięci (w produkcji użyj prawdziwej bazy)
# WAŻNE: Dane w tej bazie danych ZOSTANĄ UTRACONE po każdym restarcie serwera.
# Funkcje eksportu/importu służą do ich zachowania.
users_db = {}

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
        
        # Sprawdź czy użytkownik już istnieje
        is_existing_user = username in users_db
        
        if not is_existing_user:
            # Utwórz nowego użytkownika
            users_db[username] = {
                'id': str(int(datetime.now().timestamp() * 1000)),
                'username': username,
                'created_at': datetime.now().isoformat(),
                'link': f'tbh.fun/{username}',
                'messages': []
            }
        
        print(f"Użytkownik {'zalogowany' if is_existing_user else 'utworzony'}: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Zalogowano pomyślnie!' if is_existing_user else 'Konto utworzone!',
            'isNew': not is_existing_user,
            'data': {
                'username': username,
                'link': f'tbh.fun/{username}'
            }
        }), 200
        
    except Exception as e:
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
        
        exists = username in users_db
        
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

        if username in users_db:
            user_data = users_db[username]
            return jsonify({
                'exists': True,
                'username': user_data['username'],
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
    """Wyślij anonimową wiadomość do użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Brak danych'
            }), 400
        
        recipient = data.get('to', '').strip() # Zmieniono 'recipient' na 'to' aby pasowało do frontendu
        message = data.get('message', '').strip()
        
        if not recipient or not message:
            return jsonify({
                'success': False,
                'message': 'Odbiorca i wiadomość są wymagane'
            }), 400
        
        if len(message) > 1000: # Zmieniono limit na 1000 znaków, aby pasował do frontendu
            return jsonify({
                'success': False,
                'message': 'Wiadomość nie może być dłuższa niż 1000 znaków'
            }), 400
        
        # Sprawdź czy odbiorca istnieje
        if recipient not in users_db:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        # Dodaj wiadomość
        new_message = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        users_db[recipient]['messages'].append(new_message)
        
        print(f"Wiadomość wysłana do {recipient}")
        
        return jsonify({
            'success': True,
            'message': 'Wiadomość wysłana!'
        })
        
    except Exception as e:
        print(f"Błąd podczas wysyłania wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera'
        }), 500

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
        
        if username not in users_db:
            return jsonify({
                'success': False,
                'message': 'Użytkownik nie istnieje'
            }), 404
        
        messages = users_db[username]['messages']
        
        # Oznacz wiadomości jako przeczytane (tworzymy kopię, aby nie modyfikować oryginalnej listy podczas iteracji)
        # i sortujemy, aby najnowsze były na górze
        messages_to_return = sorted(messages, key=lambda x: x['timestamp'], reverse=True)
        
        for msg in messages: # Oznaczamy oryginalne wiadomości jako przeczytane
            msg['read'] = True
        
        return jsonify({
            'success': True,
            'messages': messages_to_return,
            'count': len(messages_to_return)
        })
        
    except Exception as e:
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
        
        if username in users_db:
            del users_db[username]
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
        
        if username in users_db:
            users_db[username]['messages'] = [] # Wyczyść listę wiadomości
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
        print(f"Błąd podczas czyszczenia wiadomości: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Błąd serwera podczas czyszczenia wiadomości.'
        }), 500

# ===== NOWE ENDPOINTY DLA EKSPORTU/IMPORTU DANYCH =====
@app.route('/export_all_data', methods=['GET'])
def export_all_data():
    """Eksportuje wszystkie dane użytkowników z bazy danych w pamięci."""
    try:
        # Zwracamy kopię, aby uniknąć problemów z modyfikacją oryginalnego słownika
        # podczas serializacji.
        return jsonify({
            'success': True,
            'data': users_db.copy(),
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
    """Importuje wszystkie dane użytkowników do bazy danych w pamięci.
    UWAGA: Ta operacja ZASTĄPI wszystkie istniejące dane."""
    global users_db # Musimy użyć global, aby zmodyfikować globalny słownik
    try:
        data = request.get_json()
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'success': False,
                'message': 'Brak danych JSON lub nieprawidłowy format (oczekiwano obiektu).'
            }), 400
        
        # Prosta walidacja struktury importowanych danych
        # Możesz dodać bardziej rygorystyczną walidację, jeśli potrzebujesz
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

        users_db.clear() # Wyczyść bieżącą bazę danych
        users_db.update(data) # Zastąp danymi z importu
        
        print(f"Dane zaimportowane pomyślnie. Liczba użytkowników: {len(users_db)}")
        return jsonify({
            'success': True,
            'message': f'Dane zaimportowane pomyślnie. Zaimportowano {len(users_db)} użytkowników.'
        }), 200
    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'message': 'Nieprawidłowy format JSON.'
        }), 400
    except Exception as e:
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
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'endpoints': {
            'register': 'POST /register',
            'check_user': 'GET /check_user?user=USERNAME',
            'get_user_details': 'GET /get_user_details?username=USERNAME',
            'send_message': 'POST /send_message',
            'get_messages': 'GET /get_messages?user=USERNAME',
            'delete_user': 'DELETE /delete_user',
            'clear_messages': 'POST /clear_messages',
            'export_all_data': 'GET /export_all_data', # Dodano
            'import_all_data': 'POST /import_all_data' # Dodano
        }
    })

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'users_count': len(users_db) # Zaktualizowano dla bazy w pamięci
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
        for username, data in users_db.items():
            users_list.append({
                'username': username,
                'created_at': data['created_at'],
                'messages_count': len(data['messages'])
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
            'GET /export_all_data', # Dodano
            'POST /import_all_data' # Dodano
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
    print("   GET /export_all_data - eksportuj wszystkie dane") # Dodano
    print("   POST /import_all_data - importuj wszystkie dane") # Dodano
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )

