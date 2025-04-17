from flask import Flask, request, jsonify, session
from flaskext.mysql import MySQL
from flask_cors import CORS
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import re
import json
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-key')
app.permanent_session_lifetime = timedelta(days=7)  # Optional: session lasts 7 days
CORS(app, supports_credentials=True)

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Change to True in production (with HTTPS)

# MySQL config
app.config['MYSQL_DATABASE_HOST'] = '88.200.86.10'
app.config['MYSQL_DATABASE_USER'] = '2024_TB_03'
app.config['MYSQL_DATABASE_PASSWORD'] = '1AH2DesOY'
app.config['MYSQL_DATABASE_DB'] = '2024_TB_03'

# cd C:\xampp\htdocs\AgroTla 
# python app.py



mysql = MySQL()
mysql.init_app(app)

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({'status': 'error', 'message': 'Missing fields'}), 400
        if len(password) < 6:
            return jsonify({'status': 'error', 'message': 'Password too short (min 6 chars)'}), 400
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({'status': 'error', 'message': 'Invalid email'}), 400

        password_hash = generate_password_hash(password)

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s OR username = %s", (email, username))
        if cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Email or username already exists'}), 409

        cursor.execute("""
            INSERT INTO users (username, first_name, last_name, email, password_hash)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, first_name, last_name, email, password_hash))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'registered'}), 201
    except Exception as e:
        print("Registration error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user_input = data.get('user_input')
        password = data.get('password')

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, password_hash
            FROM users
            WHERE email = %s OR username = %s
        """, (user_input, user_input))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[2], password):
            session.permanent = True
            session['user_id'] = user[0]
            session['username'] = user[1]
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print("Login error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/check-session')
def check_session():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user_id': session['user_id'],
            'username': session['username']
        })
    else:
        return jsonify({'logged_in': False})
    
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'logged_out'})


@app.route('/get-user-fields')
def get_user_fields():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    user_id = session['user_id']
    try:
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, coordinates, area, name FROM fields WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()
        fields = [{'id': row[0], 'coordinates': row[1], 'area': row[2], 'name': row[3]} for row in rows]
        cursor.close()
        conn.close()
        return jsonify({'fields': fields})
    except Exception as e:
        print("Error fetching user fields:", e)
        return jsonify({'error': str(e)}), 500




@app.route('/save-field', methods=['POST'])
def save_field():
    try:
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

        data = request.get_json()
        coordinates = data.get('coordinates')
        area = data.get('area')
        name = data.get('name', 'Untitled Field')

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO fields (coordinates, area, name, user_id) VALUES (%s, %s, %s, %s)",
            (json.dumps(coordinates), area, name, session['user_id'])
        )
        conn.commit()
        field_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({'status': 'saved', 'field_id': field_id})
    except Exception as e:
        print("Error saving field:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/update-field-name/<int:field_id>', methods=['POST'])
def update_field_name(field_id):
    try:
        data = request.get_json()
        new_name = data.get('name')

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE fields SET name = %s WHERE id = %s", (new_name, field_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'updated'})
    except Exception as e:
        print("Error updating field name:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/save-soil', methods=['POST'])
def save_soil():
    try:
        data = request.get_json()
        field_id = data.get('field_id')
        lat = data.get('lat')
        lng = data.get('lng')
        ph = data.get('ph')
        n = data.get('n')
        p = data.get('p')
        k = data.get('k')

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO soil_samples (field_id, lat, lng, ph, n, p, k) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (field_id, lat, lng, ph, n, p, k)
        )
        conn.commit()
        pin_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({'status': 'soil saved', 'id': pin_id})
    except Exception as e:
        print("Soil Save Error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/get-user-fields-with-pins')
def get_user_fields_with_pins():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    user_id = session['user_id']
    try:
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, coordinates, name FROM fields WHERE user_id = %s", (user_id,))
        fields = cursor.fetchall()

        result = []
        for f in fields:
            field_id, coords, field_name = f
            cursor.execute("""
                SELECT id, lat, lng, ph, n, p, k, updated_at
                FROM soil_samples
                WHERE field_id = %s
            """, (field_id,))
            pins = [
                {
                    'id': r[0],
                    'lat': r[1],
                    'lng': r[2],
                    'ph': r[3],
                    'n': r[4],
                    'p': r[5],
                    'k': r[6],
                    'updated_at': r[7].strftime('%Y-%m-%d %H:%M:%S'),
                    'field_name': field_name
                } for r in cursor.fetchall()
            ]
            result.append({
                'id': field_id,
                'coordinates': coords,
                'name': field_name,
                'pins': pins
            })

        cursor.close()
        conn.close()
        return jsonify({'fields': result})
    except Exception as e:
        print("Error:", e)
        return jsonify({'error': str(e)}), 500

    
@app.route('/delete-soil-pin/<int:pin_id>', methods=['DELETE'])
def delete_soil_pin(pin_id):
    try:
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM soil_samples WHERE id = %s", (pin_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'deleted'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete-field/<int:field_id>', methods=['DELETE'])
def delete_field(field_id):
    try:
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM soil_samples WHERE field_id = %s", (field_id,))
        cursor.execute("DELETE FROM fields WHERE id = %s", (field_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'deleted'})
    except Exception as e:
        print("Error deleting field:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update-field/<int:field_id>', methods=['POST'])
def update_field(field_id):
    try:
        data = request.get_json()
        coordinates = data.get('coordinates')
        area = data.get('area')

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE fields SET coordinates = %s, area = %s WHERE id = %s",
            (json.dumps(coordinates), area, field_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'updated'})
    except Exception as e:
        print("Update Error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/update-soil-pin/<int:pin_id>', methods=['POST'])
def update_soil_pin(pin_id):
    try:
        data = request.get_json()
        ph = data.get('ph')
        n = data.get('n')
        p = data.get('p')
        k = data.get('k')

        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE soil_samples
            SET ph = %s, n = %s, p = %s, k = %s
            WHERE id = %s
        """, (ph, n, p, k, pin_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'updated'})
    except Exception as e:
        print("Error updating soil pin:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/debug-session')
def debug_session():
    print("SESSION DEBUG:", session)
    return jsonify({
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'session_keys': list(session.keys())
    })



# ✅ Run app
if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)