from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///messages.db').replace('postgres://', 'postgresql://', 1)  # Fix dla Render
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
db = SQLAlchemy(app)

# Modele (bez zmian)
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))

# Stwórz przykładowego użytkownika (tylko do testów!)
with app.app_context():
    db.create_all()
    if not User.query.first():
        test_user = User(username="test_user")
        db.session.add(test_user)
        db.session.commit()

# Routy (bez zmian)
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/send_message/<user_id>', methods=['POST'])
def send_message(user_id):
    content = request.form.get('content')
    if content:
        new_message = Message(content=content, user_id=user_id)
        db.session.add(new_message)
        db.session.commit()
    return redirect(url_for('profile', user_id=user_id))

@app.route('/profile/<user_id>')
def profile(user_id):
    user = User.query.get(user_id)
    messages = Message.query.filter_by(user_id=user_id).all()
    return render_template('profile.html', user=user, messages=messages)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
