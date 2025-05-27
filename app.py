from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import uuid
import os

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tajny-klucz-123')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///messages.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Modele
class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Rejestracja
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Nazwa użytkownika jest już zajęta!', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('profile', username=username))
    
    return render_template('register.html')

# Logowanie
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        
        if user:
            login_user(user)
            return redirect(url_for('profile', username=username))
        else:
            flash('Nieprawidłowa nazwa użytkownika!', 'danger')
    
    return render_template('login.html')

# Wylogowanie
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Profil
@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    messages = Message.query.filter_by(user_id=user.id).all()
    return render_template('profile.html', user=user, messages=messages)

# Wysyłanie wiadomości
@app.route('/send_message/<username>', methods=['POST'])
def send_message(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('Użytkownik nie istnieje!', 'danger')
        return redirect(url_for('home'))
    
    content = request.form.get('content')
    if content:
        new_message = Message(content=content, user_id=user.id)
        db.session.add(new_message)
        db.session.commit()
        flash('Wiadomość wysłana!', 'success')
    
    return redirect(url_for('profile', username=username))

# Strona główna
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
