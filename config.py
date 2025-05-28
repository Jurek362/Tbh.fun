class Config:
    # Ustaw parametry tajne i połączenie do bazy danych
    SECRET_KEY = 'a-very-secret-key-12345'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:password@localhost:5432/ngl_clone_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
