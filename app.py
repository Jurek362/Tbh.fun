from flask import Flask, render_template, request, redirect, url_for, jsonify, g
import sqlite3
import os
import uuid # Used for generating unique identifiers

# Flask application configuration
# template_folder='.' and static_folder='.' tell Flask to look for templates
# and static files (like style.css) in the same directory as app.py.
app = Flask(__name__, template_folder='.', static_folder='.')
app.config['DATABASE'] = 'database.db' # SQLite database file name

# --- Database Initialization and Management ---

def init_db():
    """
    Initializes the database schema if tables do not exist.
    Also adds a default user for testing purposes if no users are present.
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Create 'users' table: stores user profiles for NGL-like functionality.
        # 'uid' is a unique identifier, 'username' is also unique for easy URL access.
        # 'avatar' uses an external placeholder URL as local files are not allowed.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                avatar TEXT DEFAULT 'https://placehold.co/40x40/EC1187/ffffff?text=AV', -- External URL for avatar
                region TEXT DEFAULT 'PL',
                game_id TEXT
            )
        ''')

        # Create 'messages' table: stores anonymous messages sent to users.
        # 'user_id' links to the 'users' table.
        # 'device_id' is a client-generated ID for basic tracking (not for security).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                device_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.commit() # Commit changes to the database

        # Check if the default user 'lsjulia_t' exists. If not, create it.
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'lsjulia_t'")
        if cursor.fetchone()[0] == 0:
            default_uid = str(uuid.uuid4()) # Generate a unique ID for the default user
            default_avatar_url = 'https://placehold.co/40x40/EC1187/ffffff?text=LS'
            cursor.execute("INSERT INTO users (uid, username, avatar, region, game_id) VALUES (?, ?, ?, ?, ?)",
                           (default_uid, 'lsjulia_t', default_avatar_url, 'PL', 'some_game_id'))
            db.commit()
            print("Domyślny użytkownik 'lsjulia_t' dodany do bazy danych.")

def get_db():
    """
    Establishes a connection to the SQLite database.
    The connection is stored in Flask's 'g' object to be reused within the same request.
    'sqlite3.Row' allows accessing columns by name (e.g., row['username']).
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DATES # Automatically parse date/time strings
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """
    Closes the database connection at the end of the request context.
    Ensures that database resources are properly released.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Application Routes ---

@app.route('/')
def home():
    """
    Renders the main landing page of the application.
    This is the entry point for users who visit the base URL.
    """
    return render_template('index.html')

@app.route('/<username>')
def user_profile(username):
    """
    Renders the profile page for a specific user, allowing others to send messages.
    If the requested username does not exist, a new user profile is created on the fly.
    """
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if not user:
        # If user does not exist, create a new one.
        new_uid = str(uuid.uuid4())
        # Use a placeholder avatar URL that includes the first letter of the username.
        new_avatar_url = f'https://placehold.co/40x40/EC1187/ffffff?text={username[0].upper()}'
        try:
            db.execute("INSERT INTO users (uid, username, avatar, region, game_id) VALUES (?, ?, ?, ?, ?)",
                       (new_uid, username, new_avatar_url, 'PL', str(uuid.uuid4()))) # Assign a new game_id
            db.commit()
            print(f"Nowy użytkownik '@{username}' utworzony pomyślnie.")
            # Fetch the newly created user to ensure all data is available
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        except sqlite3.IntegrityError as e:
            # Handle potential race conditions where another request might have created the user
            print(f"Błąd integralności podczas tworzenia użytkownika {username}: {e}. Próba pobrania istniejącego użytkownika.")
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if not user:
                 return "Nie można stworzyć profilu użytkownika. Spróbuj ponownie lub wybierz inną nazwę.", 500
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas tworzenia użytkownika {username}: {e}")
            return "Wystąpił nieoczekiwany błąd podczas tworzenia profilu.", 500

    # Prepare user data to be passed to the template
    user_profile_data = {
        'username': user['username'],
        'uid': user['uid'],
        'avatar': user['avatar'],
        'region': user['region'],
        'game_id': user['game_id']
    }
    # Render the 'send.html' template for the user's profile
    return render_template('send.html', user_profile=user_profile_data)


@app.route('/send_message/<uid>', methods=['POST'])
def send_message_post(uid):
    """
    Handles the submission of anonymous messages via POST request.
    Saves the message to the database and redirects to a confirmation page.
    """
    question = request.form.get('question')
    device_id = request.form.get('deviceId')

    if not question or not question.strip(): # Ensure message is not empty or just whitespace
        return "Treść wiadomości nie może być pusta.", 400

    db = get_db()
    # Retrieve user by UID to link the message correctly
    user = db.execute('SELECT id, username FROM users WHERE uid = ?', (uid,)).fetchone()

    if user:
        user_id = user['id']
        user_username = user['username']
        try:
            db.execute('INSERT INTO messages (user_id, message, device_id) VALUES (?, ?, ?)',
                       (user_id, question.strip(), device_id)) # Strip whitespace from message
            db.commit()
            # Redirect to a confirmation page, passing relevant user data
            user_profile_data = {'username': user_username}
            return render_template('sent.html', user_profile=user_profile_data)
        except Exception as e:
            print(f"Błąd podczas zapisywania wiadomości: {e}")
            return "Wystąpił błąd podczas wysyłania wiadomości. Spróbuj ponownie.", 500
    else:
        return "Nieprawidłowy UID użytkownika. Wiadomość nie może zostać wysłana.", 400

@app.route('/dashboard/<username>')
def dashboard(username):
    """
    Displays the messages received by a specific user.
    NOTE: In a real application, this route would require robust authentication
    to ensure only the profile owner can view their messages.
    """
    db = get_db()
    user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if user:
        # Fetch messages for the user, ordered by timestamp (newest first)
        messages = db.execute('SELECT message, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp DESC', (user['id'],)).fetchall()
        return render_template('dashboard.html', username=username, messages=messages)
    else:
        return "Użytkownik nie znaleziony.", 404

# --- Application Entry Point ---
if __name__ == '__main__':
    # Initialize the database when the application starts.
    # This ensures the database file and tables are created before the app runs.
    if not os.path.exists(app.config['DATABASE']):
        print(f"Plik bazy danych nie znaleziony. Tworzenie {app.config['DATABASE']}...")
    init_db()
    # Run the Flask application.
    # 'debug=True' enables reloader and debugger (for development).
    # 'host='0.0.0.0'' makes the server accessible externally (important for Render).
    # 'port' uses the environment variable PORT provided by Render, or defaults to 5000.
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
