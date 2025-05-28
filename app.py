from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config.Config')
db = SQLAlchemy(app)

# Definicja modeli bazy danych
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    messages = db.relationship('Message', backref='user', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Tworzenie tabel w bazie danych przed pierwszym żądaniem
@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' in session:
        return redirect(url_for('inbox'))
    if request.method == 'POST':
        username = request.form['username']
        return redirect(url_for('ask', username=username))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('inbox'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            flash('Hasła nie są zgodne')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Użytkownik o podanej nazwie już istnieje')
            return redirect(url_for('register'))
        new_user = User(username=username, email=email,
                        password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Rejestracja zakończona sukcesem. Zaloguj się.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('inbox'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('inbox'))
        else:
            flash('Nieprawidłowa nazwa użytkownika lub hasło')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    messages = user.messages[::-1]  # Odwróć kolejność, aby najnowsze były na górze
    return render_template('inbox.html', messages=messages,
                           username=session.get('username'))

@app.route('/ask/<username>', methods=['GET', 'POST'])
def ask(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return "Użytkownik nie istnieje", 404
    if request.method == 'POST':
        content = request.form['content']
        new_message = Message(content=content, user=user)
        db.session.add(new_message)
        db.session.commit()
        flash('Wiadomość wysłana pomyślnie!')
        return redirect(url_for('ask', username=username))
    return render_template('ask.html', recipient=username)

if __name__ == '__main__':
    app.run()
