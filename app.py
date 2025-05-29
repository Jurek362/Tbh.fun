from flask import Flask, render_template, request, redirect, url_for, g, flash
import sqlite3
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Flask application configuration
app = Flask(__name__, template_folder='.', static_folder='.')
app.config['DATABASE'] = 'database.db'
app.config['SECRET_KEY'] = 'your_super_secret_key_here_change_this_in_production' # Zmień to na silny, losowy klucz!

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home' # Redirect to home if login is required

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password_hash, avatar, region, game_id):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.avatar = avatar
        self.region = region
        self.game_id = game_id

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_data = db.execute('SELECT id, username, password_hash, avatar, region, game_id FROM users WHERE id = ?', (user_id,)).fetchone()
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['password_hash'], user_data['avatar'], user_data['region'], user_data['game_id'])
    return None

# --- Database Initialization and Management ---

def init_db():
    """
    Initializes the database schema if tables do not exist.
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Create 'users' table with password_hash
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                avatar TEXT DEFAULT 'https://placehold.co/40x40/667eea/ffffff?text=AV',
                region TEXT DEFAULT 'PL',
                game_id TEXT
            )
        ''')

        # Create 'messages' table
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
        db.commit()

        # Add a default user for testing if none exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'lsjulia_t'")
        if cursor.fetchone()[0] == 0:
            default_uid = str(uuid.uuid4())
            # Hash a default password for the default user
            default_password_hash = generate_password_hash('password123') # Zmień to hasło!
            default_avatar_url = 'https://placehold.co/40x40/667eea/ffffff?text=LS'
            cursor.execute("INSERT INTO users (uid, username, password_hash, avatar, region, game_id) VALUES (?, ?, ?, ?, ?, ?)",
                           (default_uid, 'lsjulia_t', default_password_hash, default_avatar_url, 'PL', 'some_game_id'))
            db.commit()
            print("Domyślny użytkownik 'lsjulia_t' dodany do bazy danych.")

def get_db():
    """Establishes a connection to the SQLite database."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DATES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Application Routes ---

@app.route('/')
def home():
    """Renders the main landing page with login/registration forms."""
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    """Handles user registration."""
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()

    if not username or not password:
        flash('Nazwa użytkownika i hasło nie mogą być puste!', 'error')
        return redirect(url_for('home'))
    if len(username) < 3:
        flash('Nazwa użytkownika musi mieć minimum 3 znaki!', 'error')
        return redirect(url_for('home'))
    if not username.isalnum() and '_' not in username: # Allow alphanumeric and underscore
        flash('Nazwa użytkownika może zawierać tylko litery, cyfry i podkreślenia!', 'error')
        return redirect(url_for('home'))
    if len(password) < 6:
        flash('Hasło musi mieć minimum 6 znaków!', 'error')
        return redirect(url_for('home'))

    db = get_db()
    existing_user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing_user:
        flash('Nazwa użytkownika już istnieje!', 'error')
        return redirect(url_for('home'))

    try:
        hashed_password = generate_password_hash(password)
        new_uid = str(uuid.uuid4())
        new_avatar_url = f'https://placehold.co/40x40/667eea/ffffff?text={username[0].upper()}'
        db.execute("INSERT INTO users (uid, username, password_hash, avatar, region, game_id) VALUES (?, ?, ?, ?, ?, ?)",
                   (new_uid, username, hashed_password, new_avatar_url, 'PL', str(uuid.uuid4())))
        db.commit()
        flash('Rejestracja zakończona sukcesem! Możesz się zalogować.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Błąd rejestracji: {e}', 'error')
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    """Handles user login."""
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()

    db = get_db()
    user_data = db.execute('SELECT id, username, password_hash, avatar, region, game_id FROM users WHERE username = ?', (username,)).fetchone()

    if user_data and check_password_hash(user_data['password_hash'], password):
        user = User(user_data['id'], user_data['username'], user_data['password_hash'], user_data['avatar'], user_data['region'], user_data['game_id'])
        login_user(user)
        flash('Zalogowano pomyślnie!', 'success')
        return redirect(url_for('dashboard', username=username))
    else:
        flash('Nieprawidłowa nazwa użytkownika lub hasło.', 'error')
        return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    logout_user()
    flash('Wylogowano pomyślnie.', 'info')
    return redirect(url_for('home'))

@app.route('/<username>')
def send_message_page(username):
    """
    Renders the page for sending anonymous messages to a specific user.
    This page does NOT require login.
    """
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if not user:
        # If user does not exist, provide an option to create or show error
        flash(f'Użytkownik @{username} nie istnieje. Stwórz go lub sprawdź pisownię.', 'error')
        return redirect(url_for('home'))

    user_profile_data = {
        'username': user['username'],
        'uid': user['uid'],
        'avatar': user['avatar'],
        'region': user['region'],
        'game_id': user['game_id']
    }
    return render_template('send.html', user_profile=user_profile_data)


@app.route('/send_message/<uid>', methods=['POST'])
def send_message_post(uid):
    """
    Handles the submission of anonymous messages.
    This endpoint does NOT require login.
    """
    message_content = request.form.get('messageText')
    device_id = request.form.get('deviceId')

    if not message_content or not message_content.strip():
        flash('Treść wiadomości nie może być pusta.', 'error')
        return redirect(request.referrer or url_for('home')) # Redirect back or to home

    db = get_db()
    user = db.execute('SELECT id, username FROM users WHERE uid = ?', (uid,)).fetchone()

    if user:
        user_id = user['id']
        user_username = user['username']
        try:
            db.execute('INSERT INTO messages (user_id, message, device_id) VALUES (?, ?, ?)',
                       (user_id, message_content.strip(), device_id))
            db.commit()
            user_profile_data = {'username': user_username}
            flash('Wiadomość została wysłana!', 'success')
            return render_template('sent.html', user_profile=user_profile_data)
        except Exception as e:
            db.rollback()
            flash(f'Wystąpił błąd podczas wysyłania wiadomości: {e}', 'error')
    else:
        flash('Nieprawidłowy odbiorca wiadomości.', 'error')
    return redirect(request.referrer or url_for('home')) # Redirect back or to home


@app.route('/dashboard')
@login_required # This decorator ensures only logged-in users can access this route
def dashboard():
    """
    Displays the messages received by the currently logged-in user.
    """
    db = get_db()
    # Fetch messages for the current_user (who is logged in)
    messages = db.execute('SELECT message, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp DESC', (current_user.id,)).fetchall()
    
    user_profile_data = {
        'username': current_user.username,
        'avatar': current_user.avatar
    }
    return render_template('dashboard.html', user_profile=user_profile_data, messages=messages)

# --- Application Entry Point ---
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        print(f"Plik bazy danych nie znaleziony. Tworzenie {app.config['DATABASE']}...")
    init_db()
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))

