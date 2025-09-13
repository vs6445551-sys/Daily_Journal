from flask import Flask, request, jsonify, session, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from functools import wraps

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
DATABASE = 'journal.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )"""
    )
    conn.commit()
    conn.close()

# --- Static pages (no templates) ---
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/signup')
def signup_page():
    return send_from_directory('static', 'signup.html')

@app.route('/home')
def home_page():
    if 'user_id' not in session:
        return redirect('/')
    return send_from_directory('static', 'home.html')

# --- API ---
@app.route('/api/me')
def api_me():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session.get('username')})
    return jsonify({'logged_in': False})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'success': False, 'error': 'Missing username or password'}), 400
    hashed = generate_password_hash(password)
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
        conn.commit()
        user_id = c.lastrowid
        session['user_id'] = user_id
        session['username'] = username
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Username already exists'}), 409
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'success': False, 'error': 'Missing username or password'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row and check_password_hash(row['password'], password):
        session['user_id'] = row['id']
        session['username'] = row['username']
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/entries', methods=['GET', 'POST'])
@login_required
def api_entries():
    user_id = session['user_id']
    if request.method == 'GET':
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, title, content, created_at, updated_at FROM entries WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        rows = c.fetchall()
        conn.close()
        entries = [dict(r) for r in rows]
        return jsonify({'success': True, 'entries': entries})

    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO entries (user_id, title, content) VALUES (?, ?, ?)', (user_id, title, content))
    conn.commit()
    entry_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'entry_id': entry_id})

@app.route('/api/entries/<int:entry_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_entry(entry_id):
    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM entries WHERE id = ? AND user_id = ?', (entry_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Not found'}), 404

    if request.method == 'GET':
        entry = dict(row)
        conn.close()
        return jsonify({'success': True, 'entry': entry})

    if request.method == 'PUT':
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        content = (data.get('content') or '').strip()
        c.execute('UPDATE entries SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (title, content, entry_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    c.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/view')
def view_page():
    return send_from_directory('static', 'view.html')


@app.route('/api/entries', methods=['GET'])
def get_entries():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect('journal.db')
    c = conn.cursor()
    c.execute("SELECT id, title, content, created_at, updated_at FROM entries WHERE user_id = ?", (session["user_id"],))
    rows = c.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "created_at": row[3],
            "updated_at": row[4]
        })
    return jsonify(entries)


if __name__ == '__main__':
    init_db()  # ✅ call DB init once at startup
    app.run(debug=True)

