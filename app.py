from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, flash, session
from flask_pymongo import PyMongo
from bson import ObjectId
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import qrcode
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'  
app.config["MONGO_URI"] = "mongodb://localhost:27017/mydatabase"
db = PyMongo(app).db

orders_collection = db.orders

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    user_data = db.Users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        user = User()
        user.id = str(user_data['_id'])
        user.username = user_data['username'] 
        return user
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if session.get('role') == 'teacher':
            flash('Teachers cannot register new accounts.', 'error')
            return redirect(url_for('login'))

        if db.Users.find_one({"username": username}):
            return render_template('register.html', error='Username already exists')

        db.Users.insert_one({"username": username, "password": password, "role": "student"})
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = db.Users.find_one({"username": username, "password": password})

        if user_data:
            user = User()
            user.id = str(user_data['_id'])
            login_user(user)

            if user_data['role'] == 'admin':
                return redirect(url_for('admin'))
            elif user_data['role'] == 'teacher':
                session['role'] = 'teacher' 
                return redirect(url_for('menu', table_number=1))  
            else:
                return redirect(url_for('menu', table_number=1))  

        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    session.pop('role', None)  
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu/<table_number>', methods=['GET', 'POST'])
def menu(table_number):
    if current_user.is_authenticated:
        if request.method == 'POST':
            cart_item = {
                "name": request.form['item_name'],
                "quantity": int(request.form['quantity']),
                "price": float(request.form['price']),
            }
            if 'cart' not in session:
                session['cart'] = []
            session['cart'].append(cart_item)

        return render_template('menu.html', table_number=table_number, cart=session.get('cart', []))
    else:
        return redirect(url_for('login'))

@app.route('/generate_qr/<table_number>')
def generate_qr(table_number):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        menu_url = f'http://127.0.0.1:8080/menu/{table_number}'
        qr.add_data(menu_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img_path = os.path.join('static', 'qrcodes', f'table_{table_number}.png')
        img.save(img_path)

        return send_from_directory('static/qrcodes', f'table_{table_number}.png')
    except Exception as e:
        print(f"Exception: {e}")
        return str(e)

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    if request.method == 'POST':
        user_id = current_user.get_id()
        user_data = db.Users.find_one({"_id": ObjectId(user_id)})
        username = user_data['username']
        order_details = request.json 

        current_time = datetime.now()

        print(f"Username: {username}, User ID: {user_id}, Order details: {order_details}, Order Time: {current_time}")

        orders_collection.insert_one({
            "username": username,
            "user_id": user_id,
            "order_details": order_details,
            "order_time": current_time,
            "table_number": order_details.get("table_number")
        })

        return jsonify({"message": "Order placed successfully!", "username": username})

@app.route('/admin')
@login_required
def admin():
    if current_user.is_authenticated:
        all_orders = list(orders_collection.find().sort('order_time', -1)) 
        for order in all_orders:
            username = order.get('username')  
            if username:
                user = db.Users.find_one({"username": username})
                if user:
                    order['role'] = user.get('role', 'guest') 
                else:
                    order['role'] = 'guest' 
            else:
                order['role'] = 'guest' 
        return render_template('admin.html', orders=all_orders)
    else:
        return redirect(url_for('login'))

    
@app.route('/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    if request.method == 'POST':
        data = request.get_json() 
        order_id = data.get('order_id')
        status = data.get('status')

        result = orders_collection.update_one(
            {'_id': order_id},  
            {'$set': {'status': status}} 
        )

        if result.modified_count > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to update order status'})

@app.route('/services/<table_number>')
def services(table_number):
    if current_user.is_authenticated:
        return render_template('services.html', table_number=table_number)
    else:
        return redirect(url_for('login'))

@app.route('/contact/<table_number>')
def contact(table_number):
    if current_user.is_authenticated:
        return render_template('contact.html', table_number=table_number)
    else:
        return redirect(url_for('login'))

@app.route('/about/<table_number>')
def about(table_number):
    if current_user.is_authenticated:
        return render_template('about.html', table_number=table_number)
    else:
        return redirect(url_for('login'))

@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.is_authenticated and session.get('role') == 'teacher':
        return render_template('teacher_dashboard.html')
    else:
        return redirect(url_for('login'))

@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        teacher_data = db.Users.find_one({"username": username, "password": password, "role": "teacher"})
        
        if teacher_data:  # If the teacher exists in the database with the correct role
            user = User()
            user.id = str(teacher_data['_id'])  # Use the teacher's unique ID
            login_user(user)
            session['role'] = 'teacher'  # Set 'teacher' role in session
            return redirect(url_for('menu', table_number=1))

        else:
            flash('Invalid teacher credentials', 'error')

    return render_template('teacher_login.html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)
