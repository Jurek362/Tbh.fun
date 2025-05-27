const express = require('express');
const { Pool } = require('pg');
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

// Połączenie z bazą danych Postgres
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

// Inicjalizacja bazy danych
async function initDb() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS qa_sessions (
      id UUID PRIMARY KEY,
      password_hash TEXT NOT NULL
    );
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS questions (
      id SERIAL PRIMARY KEY,
      qa_id UUID REFERENCES qa_sessions(id),
      question_text TEXT NOT NULL,
      status TEXT DEFAULT 'pending',
      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `);
}
initDb();

// Tworzenie nowej sesji Q&A
app.post('/create-qa', async (req, res) => {
  const { password } = req.body;
  if (!password) return res.status(400).send('Hasło jest wymagane');
  const saltRounds = 10;
  const passwordHash = await bcrypt.hash(password, saltRounds);
  const uuid = uuidv4();
  try {
    await pool.query('INSERT INTO qa_sessions (id, password_hash) VALUES ($1, $2)', [uuid, passwordHash]);
    res.status(201).json({
      id: uuid,
      askLink: `/ask/${uuid}`,
      viewLink: `/qa/${uuid}/questions`
    });
  } catch (err) {
    res.status(500).send('Błąd podczas tworzenia sesji');
  }
});

// Dodawanie pytania
app.post('/ask/:uuid', async (req, res) => {
  const { uuid } = req.params;
  const { question } = req.body;
  if (!question) return res.status(400).send('Pytanie jest wymagane');
  try {
    const result = await pool.query('SELECT 1 FROM qa_sessions WHERE id = $1', [uuid]);
    if (result.rowCount === 0) return res.status(404).send('Sesja nie znaleziona');
    await pool.query('INSERT INTO questions (qa_id, question_text, status) VALUES ($1, $2, $3)', [uuid, question, 'pending']);
    res.status(201).send('Pytanie dodane');
  } catch (err) {
    res.status(500).send('Błąd podczas dodawania pytania');
  }
});

// Przeglądanie pytań przez właściciela
app.get('/qa/:uuid/questions', async (req, res) => {
  const { uuid } = req.params;
  const { password } = req.query;
  if (!password) return res.status(400).send('Hasło jest wymagane');
  try {
    const sessionResult = await pool.query('SELECT password_hash FROM qa_sessions WHERE id = $1', [uuid]);
    if (sessionResult.rowCount === 0) return res.status(404).send('Sesja nie znaleziona');
    const match = await bcrypt.compare(password, sessionResult.rows[0].password_hash);
    if (!match) return res.status(401).send('Nieprawidłowe hasło');
    const questionsResult = await pool.query('SELECT id, question_text, status, timestamp FROM questions WHERE qa_id = $1 ORDER BY timestamp DESC', [uuid]);
    res.json(questionsResult.rows);
  } catch (err) {
    res.status(500).send('Błąd podczas pobierania pytań');
  }
});

// Przeglądanie publicznych pytań
app.get('/qa/:uuid/public', async (req, res) => {
  const { uuid } = req.params;
  try {
    const questionsResult = await pool.query('SELECT question_text, timestamp FROM questions WHERE qa_id = $1 AND status = $2 ORDER BY timestamp DESC', [uuid, 'approved']);
    res.json(questionsResult.rows);
  } catch (err) {
    res.status(500).send('Błąd podczas pobierania publicznych pytań');
  }
});

// Zatwierdzanie pytania
app.post('/qa/:uuid/approve', async (req, res) => {
  const { uuid } = req.params;
  const { question_id, password } = req.body;
  if (!question_id || !password) return res.status(400).send('ID pytania i hasło są wymagane');
  try {
    const sessionResult = await pool.query('SELECT password_hash FROM qa_sessions WHERE id = $1', [uuid]);
    if (sessionResult.rowCount === 0) return res.status(404).send('Sesja nie znaleziona');
    const match = await bcrypt.compare(password, sessionResult.rows[0].password_hash);
    if (!match) return res.status(401).send('Nieprawidłowe hasło');
    const questionResult = await pool.query('SELECT 1 FROM questions WHERE id = $1 AND qa_id = $2 AND status = $3', [question_id, uuid, 'pending']);
    if (questionResult.rowCount === 0) return res.status(404).send('Pytanie oczekujące nie znalezione');
    await pool.query('UPDATE questions SET status = $1 WHERE id = $2', ['approved', question_id]);
    res.send('Pytanie zatwierdzone');
  } catch (err) {
    res.status(500).send('Błąd podczas zatwierdzania');
  }
});

// Odrzucanie pytania
app.post('/qa/:uuid/reject', async (req, res) => {
  const { uuid } = req.params;
  const { question_id, password } = req.body;
  if (!question_id || !password) return res.status(400).send('ID pytania i hasło są wymagane');
  try {
    const sessionResult = await pool.query('SELECT password_hash FROM qa_sessions WHERE id = $1', [uuid]);
    if (sessionResult.rowCount === 0) return res.status(404).send('Sesja nie znaleziona');
    const match = await bcrypt.compare(password, sessionResult.rows[0].password_hash);
    if (!match) return res.status(401).send('Nieprawidłowe hasło');
    const questionResult = await pool.query('SELECT 1 FROM questions WHERE id = $1 AND qa_id = $2 AND status = $3', [question_id, uuid, 'pending']);
    if (questionResult.rowCount === 0) return res.status(404).send('Pytanie oczekujące nie znalezione');
    await pool.query('UPDATE questions SET status = $1 WHERE id = $2', ['rejected', question_id]);
    res.send('Pytanie odrzucone');
  } catch (err) {
    res.status(500).send('Błąd podczas odrzucania');
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Serwer działa na porcie ${PORT}`));
