# app.py - Poprawiony serwer Flask
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)

# ===== KONFIGURACJA CORS - TYLKO JEDNA! =====
# USUŃ wszystkie inne konfiguracje CORS z kodu!

CORS(app, 
     origins=['https://jurek362.github.io'],  # Tylko jeden origin
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
     supports_credentials=True)

# ===== MIDDLEWARE =====
@app.before_request
def before_request():
    # Debug logging
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")
    print(f"Origin: {request.headers.get('Origin')}")
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', 'https://jurek362.github.io')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

@app.after_request
def after_request(response):
    # Dodatkowe nagłówki bezpieczeństwa
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Debug - sprawdź nagłówki CORS
    print(f"Response headers: {dict(response.headers)}")
    
    return response

# ===== ROUTES =====

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'cors': 'enabled'
    })

@app.route('/api/create-user', methods=['POST', 'OPTIONS'])
def create_user():
    """Create new user endpoint"""
    try:
        # Handle preflight
        if request.method == 'OPTIONS':
            return jsonify({'status': 'OK'})
        
        # Get JSON data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        print(f"Creating user with data: {data}")
        
        # Validate required fields
        username = data.get('username')
        email = data.get('email')
        
        if not username or not email:
            return jsonify({
                'success': False,
                'error': 'Username and email are required'
            }), 400
        
        # Create new user object
        new_user = {
            'id': str(int(datetime.now().timestamp() * 1000)),
            'username': username.strip(),
            'email': email.strip().lower(),
            'preferences': data.get('preferences', {}),
            'created_at': datetime.now().isoformat()
        }
        
        # Here you would typically save to database
        # For now, we'll just return the user data
        
        print(f"User created successfully: {new_user['id']}")
        
        return jsonify({
            'success': True,
            'data': {
                'user': new_user,
                'message': 'User created successfully'
            }
        }), 201
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    try:
        # Here you would typically fetch from database
        user = {
            'id': user_id,
            'username': 'example_user',
            'email': 'user@example.com',
            'created_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': {'user': user}
        })
        
    except Exception as e:
        print(f"Error fetching user: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/user/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user by ID"""
    try:
        data = request.get_json()
        
        print(f"Updating user {user_id} with: {data}")
        
        # Here you would typically update in database
        updated_user = {
            'id': user_id,
            **data,
            'updated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': {'user': updated_user},
            'message': 'User updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user by ID"""
    try:
        print(f"Deleting user {user_id}")
        
        # Here you would typically delete from database
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'path': request.path
    }), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': str(error)
    }), 400

# ===== MAIN =====
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 Starting Flask server on port {port}")
    print(f"📡 CORS enabled for: https://jurek362.github.io")
    print(f"🌍 Debug mode: {debug_mode}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
