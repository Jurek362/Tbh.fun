# app.py - Flask backend z funkcjonalnością IP + Region
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests
from datetime import datetime
import threading

app = Flask(__name__)

# ===== KONFIGURACJA CORS =====
CORS(app, origins=['https://anonlink.fun'])

def get_client_ip():
    """Pobierz prawdziwy IP klienta"""
    # Sprawdź nagłówki proxy
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_ip_location(ip_address):
    """Pobierz lokalizację na podstawie IP używając ipinfo.io"""
    try:
        if ip_address in ['127.0.0.1', 'localhost', None]:
            return {
                'ip': ip_address,
                'country': 'Local',
                'region': 'Local',
                'city': 'Local',
                'timezone': 'Local'
            }
        
        # Użyj ipinfo.io API (darmowe, bez klucza do 50k requestów/miesiąc)
        response = requests.get(f'https://ipinfo.io/{ip_address}/json', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'ip': data.get('ip', ip_address),
                'country': data.get('country', 'Unknown'),
                'region': data.get('region', 'Unknown'),
                'city': data.get('city', 'Unknown'),
                'timezone': data.get('timezone', 'Unknown'),
                'org': data.get('org', 'Unknown')  # ISP info
            }
        else:
            # Fallback - spróbuj z innym API
            return get_ip_location_fallback(ip_address)
            
    except Exception as e:
        print(f"Błąd podczas pobierania lokalizacji IP: {str(e)}")
        return get_ip_location_fallback(ip_address)

def get_ip_location_fallback(ip_address):
    """Fallback API - użyj freeipapi.com"""
    try:
        response = requests.get(f'https://freeipapi.com/api/json/{ip_address}', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'ip': data.get('ipAddress', ip_address),
                'country': data.get('countryName', 'Unknown'),
                'region': data.get('regionName', 'Unknown'),
                'city': data.get('cityName', 'Unknown'),
                'timezone': data.get('timeZone', 'Unknown')
            }
        else:
            # Ostateczny fallback
            return {
                'ip': ip_address,
                'country': 'Unknown',
                'region': 'Unknown',
                'city': 'Unknown',
                'timezone': 'Unknown'
            }
            
    except Exception as e:
        print(f"Błąd fallback API: {str(e)}")
        return {
            'ip': ip_address,
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'timezone': 'Unknown'
        }

def send_user_notification(user_data, location_data):
    """Wyślij powiadomienie o nowym użytkowniku na webhook"""
    try:
        # Webhook URL - ustaw w zmiennych środowiskowych
        WEBHOOK_URL = os.environ.get('https://discord.com/api/webhooks/1379028559636725790/-q9IWcbhdl0vq3V0sKN_H3q2EeWQbs4oL7oVWkEbMMmL2xcBeyRA0pEtYDwln94jJg0r', '')
        
        if not WEBHOOK_URL:
            print("⚠️ WEBHOOK_URL nie jest skonfigurowany")
            return
        
        # Przygotuj dane do wysłania
        webhook_data = {
            'event': 'new_user_registered',
            'timestamp': datetime.now().isoformat(),
            'username': user_data['username'],
            'user_id': user_data['id'],
            'link': user_data['link'],
            'ip': location_data['ip'],
            'country': location_data['country'],
            'region': location_data['region'],
            'city': location_data['city'],
            'timezone': location_data.get('timezone', 'Unknown'),
            'isp': location_data.get('org', 'Unknown'),
            'user_agent': user_data.get('user_agent', 'Unknown'),
            'created_at': user_data['created_at']
        }
        
        # Wyślij na webhook
        headers = {'Content-Type': 'application/json'}
        response = requests.post(WEBHOOK_URL, json=webhook_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ Powiadomienie wysłane na webhook")
        else:
            print(f"❌ Błąd webhook: {response.status_code}")
        
        # Logowanie do konsoli
        print(f"""
🎉 NOWY UŻYTKOWNIK ZAREJESTROWANY:
👤 Username: {user_data['username']}
🆔 User ID: {user_data['id']}
🔗 Link: {user_data['link']}
🌍 IP: {location_data['ip']}
📍 Lokalizacja: {location_data['city']}, {location_data['region']}, {location_data['country']}
🌐 ISP: {location_data.get('org', 'Unknown')}
⏰ Czas: {user_data['created_at']}
        """)
        
    except Exception as e:
        print(f"❌ Błąd podczas wysyłania powiadomienia: {str(e)}")

def send_notification_async(user_data, location_data):
    """Wyślij powiadomienie w tle (non-blocking)"""
    thread = threading.Thread(target=send_user_notification, args=(user_data, location_data))
    thread.daemon = True
    thread.start()

@app.before_request
def log_request():
    """Debug logging"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    if request.headers.get('Origin'):
        print(f"Origin: {request.headers.get('Origin')}")

# ===== ROUTES =====

@app.route('/')
def home():
    """Root endpoint"""
    return jsonify({
        'message': 'Tbh.fun API is running',
        'status': 'OK',
        'cors_enabled': True
    })

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/create-user', methods=['POST'])
def create_user():
    """Create new user z IP i regionem"""
    try:
        # Pobierz dane JSON
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych JSON'
            }), 400
        
        # Pobierz IP klienta
        client_ip = get_client_ip()
        print(f"IP klienta: {client_ip}")
        
        # Pobierz lokalizację na podstawie IP
        location_data = get_ip_location(client_ip)
        print(f"Dane lokalizacji: {location_data}")
        
        # Loguj otrzymane dane
        print(f"Otrzymane dane: {data}")
        
        # TYLKO USERNAME - jak NGL.link
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username jest wymagany'
            }), 400
        
        if len(username) < 3:
            return jsonify({
                'success': False,
                'error': 'Username musi mieć przynajmniej 3 znaki'
            }), 400
        
        if len(username) > 20:
            return jsonify({
                'success': False,
                'error': 'Username nie może być dłuższy niż 20 znaków'
            }), 400
        
        # Sprawdź czy username zawiera tylko dozwolone znaki
        import re
        if not re.match("^[a-zA-Z0-9_-]+$", username):
            return jsonify({
                'success': False,
                'error': 'Username może zawierać tylko litery, cyfry, _ i -'
            }), 400
        
        # Utwórz użytkownika z danymi IP i lokalizacji
        user_data = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'username': username,
            'created_at': datetime.now().isoformat(),
            'link': f'tbh.fun/{username}',
            # Dodane dane IP i lokalizacji
            'registration_ip': location_data['ip'],
            'registration_country': location_data['country'],
            'registration_region': location_data['region'],
            'registration_city': location_data['city'],
            'registration_timezone': location_data['timezone'],
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
        
        # Dodaj ISP info jeśli dostępne
        if 'org' in location_data:
            user_data['registration_isp'] = location_data['org']
        
        # Tutaj dodaj logikę zapisu do bazy danych
        
        # ===== WYŚLIJ POWIADOMIENIE O NOWYM UŻYTKOWNIKU =====
        send_notification_async(user_data, location_data)
        
        print(f"Użytkownik utworzony: {user_data['id']}")
        print(f"Lokalizacja: {location_data['city']}, {location_data['region']}, {location_data['country']}")
        
        # Zwróć odpowiedź (bez wrażliwych danych IP w publicznej odpowiedzi)
        return jsonify({
            'success': True,
            'message': 'Konto utworzone pomyślnie!',
            'data': {
                'username': user_data['username'],
                'link': user_data['link'],
                'id': user_data['id'],
                'created_at': user_data['created_at'],
                # Opcjonalnie: pokazuj tylko kraj/region, nie pełny IP
                'location': f"{location_data['city']}, {location_data['region']}, {location_data['country']}"
            }
        }), 201
        
    except Exception as e:
        print(f"Błąd podczas tworzenia użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera',
            'details': str(e)
        }), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Pobierz wszystkich użytkowników"""
    try:
        # Tutaj dodaj logikę pobierania z bazy danych
        users = [
            {
                'id': '1',
                'username': 'test_user',
                'link': 'tbh.fun/test_user',
                'created_at': datetime.now().isoformat(),
                'location': 'Warsaw, Mazovia, PL'  # Przykład
            }
        ]
        
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkowników: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Pobierz użytkownika po ID"""
    try:
        # Tutaj dodaj logikę pobierania z bazy danych
        user = {
            'id': user_id,
            'username': 'example_user',
            'link': f'tbh.fun/{user_id}',
            'created_at': datetime.now().isoformat(),
            'location': 'Warsaw, Mazovia, PL'
        }
        
        return jsonify({
            'success': True,
            'data': user
        })
        
    except Exception as e:
        print(f"Błąd podczas pobierania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Aktualizuj użytkownika"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Brak danych do aktualizacji'
            }), 400
        
        # Tutaj dodaj logikę aktualizacji w bazie danych
        updated_user = {
            'id': user_id,
            **data,
            'updated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'message': 'Użytkownik zaktualizowany',
            'data': updated_user
        })
        
    except Exception as e:
        print(f"Błąd podczas aktualizacji użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

@app.route('/api/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Usuń użytkownika"""
    try:
        # Tutaj dodaj logikę usuwania z bazy danych
        
        print(f"Usunięto użytkownika: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Użytkownik usunięty'
        })
        
    except Exception as e:
        print(f"Błąd podczas usuwania użytkownika: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Błąd serwera'
        }), 500

# Dodatkowy endpoint do testowania IP
@app.route('/api/my-ip', methods=['GET'])
def get_my_ip():
    """Test endpoint - sprawdź swoje IP i lokalizację"""
    try:
        client_ip = get_client_ip()
        location_data = get_ip_location(client_ip)
        
        return jsonify({
            'success': True,
            'ip_data': location_data,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'headers': dict(request.headers)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint nie istnieje',
        'path': request.path
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
    print(f"🗺️  IP Geolocation: ipinfo.io + freeipapi.com (fallback)")
    print(f"📢 Webhook: WEBHOOK_URL")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
)
