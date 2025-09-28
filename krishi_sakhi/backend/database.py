import sqlite3
import os

DB_PATH = 'krishi.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS farmers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        name TEXT,
        age INTEGER,
        gender TEXT,
        phone TEXT,
        fcm_token TEXT,
        location_ml TEXT,
        location_en TEXT,
        lat REAL,
        lon REAL,
        crop TEXT,
        soil TEXT,
        field_type TEXT,
        farm_size REAL,
        irrigation_type TEXT,
        experience INTEGER,
        pests_history TEXT,
        yield_goals TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER,
        query TEXT,
        response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmer_id) REFERENCES farmers (id)
    )''')
    conn.commit()
    conn.close()

def save_farmer(data):
    init_db()  # Ensure table exists
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO farmers (username, name, age, gender, phone, fcm_token, location_ml, location_en, lat, lon, crop, soil, field_type, farm_size, irrigation_type, experience, pests_history, yield_goals)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['username'], data['name'], data['age'], data['gender'], data['phone'], data.get('fcm_token'), data['location_ml'], data['location_en'], data['lat'], data['lon'], data['crop'], data['soil'], data['field_type'], data['farm_size'], data['irrigation_type'], data['experience'], data['pests_history'], data['yield_goals']))
        farmer_id = c.lastrowid
        conn.commit()
        return type('obj', (object,), {'id': farmer_id})()  # Mock object with id
    except sqlite3.IntegrityError:
        return None  # Username exists
    finally:
        conn.close()

def get_farmer_data(username):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM farmers WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return type('Farmer', (object,), {
            'id': row[0], 'username': row[1], 'name': row[2], 'age': row[3], 'gender': row[4],
            'phone': row[5], 'fcm_token': row[6], 'location_ml': row[7], 'location_en': row[8],
            'lat': row[9], 'lon': row[10], 'crop': row[11], 'soil': row[12], 'field_type': row[13],
            'farm_size': row[14], 'irrigation_type': row[15], 'experience': row[16],
            'pests_history': row[17], 'yield_goals': row[18]
        })()  # Mock farmer object
    return None

def get_farmer(username):
    return get_farmer_data(username)  # Alias for consistency

def save_query(farmer_id, query, response):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO queries (farmer_id, query, response) VALUES (?, ?, ?)', (farmer_id, query, response))
    conn.commit()
    conn.close()
    return True

def update_farmer_token(farmer_id, token):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE farmers SET fcm_token = ? WHERE id = ?', (token, farmer_id))
    conn.commit()
    conn.close()
    return c.rowcount > 0
