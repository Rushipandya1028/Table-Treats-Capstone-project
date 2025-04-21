from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, flash, session
from flask_pymongo import PyMongo
from bson import ObjectId
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import qrcode
import os
from datetime import datetime
import random
from werkzeug.utils import secure_filename
import time
import json
from twilio.rest import Client
from dotenv import load_dotenv
import razorpay

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'  
app.config["MONGO_URI"] = "mongodb://localhost:27017/mydatabase"
app.config['UPLOAD_FOLDER'] = 'static/images/menu_items'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Debug logging for Twilio credentials
print(f"Twilio Account SID: {TWILIO_ACCOUNT_SID}")
print(f"Twilio Auth Token: {'*' * len(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else 'None'}")
print(f"Twilio Phone Number: {TWILIO_PHONE_NUMBER}")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    print("Warning: Some Twilio credentials are missing. SMS notifications will not work.")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Razorpay configuration
RAZORPAY_KEY_ID = 'rzp_test_mShHBu7bNrheet'  # Your test key ID
RAZORPAY_KEY_SECRET = 'hKrOiquDadGXLJJKYSniaQAn'  # Your test key secret
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Configure Razorpay test mode
razorpay_client.set_app_details({
    "title": "TableTreats",
    "version": "1.0.0"
})

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = PyMongo(app).db

def initialize_menu_items():
    # Check if menu items already exist
    if db.menu_items.count_documents({}) == 0:
        default_items = [
            {
                'name': 'Veg Club Sandwich',
                'price': 100,
                'category': 'Fast Food',
                'description': 'A delicious vegetarian sandwich with fresh vegetables',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Cheese Masala Dosa',
                'price': 160,
                'category': 'Punjabi',
                'description': 'Crispy dosa filled with cheese and masala',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Margherita Pizza',
                'price': 150,
                'category': 'Italian',
                'description': 'Classic pizza with tomato sauce and cheese',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Manchurian',
                'price': 180,
                'category': 'Chinese',
                'description': 'Vegetable balls in spicy sauce',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'White Sauce Pasta',
                'price': 200,
                'category': 'Italian',
                'description': 'Creamy pasta with white sauce',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Noodles',
                'price': 130,
                'category': 'Chinese',
                'description': 'Stir-fried noodles with vegetables',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Aloo Paratha',
                'price': 100,
                'category': 'Punjabi',
                'description': 'Stuffed flatbread with potato filling',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Samosa Chaat',
                'price': 80,
                'category': 'Fast Food',
                'description': 'Crispy samosas topped with chutneys',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Khichdi',
                'price': 90,
                'category': 'Gujarati',
                'description': 'Comforting rice and lentil dish',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Paneer Chilli',
                'price': 180,
                'category': 'Chinese',
                'description': 'Cottage cheese in spicy sauce',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Punjabi Thali',
                'price': 180,
                'category': 'Punjabi',
                'description': 'Complete meal with various dishes',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Gujarati Thali',
                'price': 200,
                'category': 'Gujarati',
                'description': 'Traditional Gujarati meal',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Pav Bhaji',
                'price': 150,
                'category': 'Fast Food',
                'description': 'Spicy vegetable curry with bread',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Chole Kulche',
                'price': 120,
                'category': 'Punjabi',
                'description': 'Chickpea curry with bread',
                'image_path': '/static/images/default-food.jpg'
            },
            {
                'name': 'Pulav',
                'price': 140,
                'category': 'Punjabi',
                'description': 'Fragrant rice with vegetables',
                'image_path': '/static/images/default-food.jpg'
            }
        ]
        db.menu_items.insert_many(default_items)

# Initialize menu items when the app starts
initialize_menu_items()

orders_collection = db.orders

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, user_data=None):
        if user_data:
            self.id = str(user_data['_id'])
            self.username = user_data['username']
            self.role = user_data.get('role', 'student')

    @property
    def is_admin(self):
        return self.role == 'admin'

@login_manager.user_loader
def load_user(user_id):
    user_data = db.Users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = db.Users.find_one({"username": username, "password": password})

        if user_data:
            user = User(user_data)
            login_user(user)

            if user.role == 'admin':
                return redirect(url_for('admin'))
            elif user.role == 'teacher':
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
    # Clear cart from localStorage by setting a script in the response
    response = redirect(url_for('login'))
    response.set_cookie('clear_cart', 'true', max_age=1)
    return response

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

        # Get menu items from database
        menu_items = list(db.menu_items.find())
        
        # Get current cart items from localStorage
        cart_items = request.args.get('cart_items', '[]')
        cart_items = json.loads(cart_items)
        
        # Filter out cart items that no longer exist in menu_items
        valid_cart_items = []
        for cart_item in cart_items:
            if any(item['name'] == cart_item['name'] for item in menu_items):
                valid_cart_items.append(cart_item)
        
        # Update localStorage with valid cart items
        return render_template('menu.html', 
                             table_number=table_number, 
                             menu_items=menu_items, 
                             cart=session.get('cart', []),
                             valid_cart_items=json.dumps(valid_cart_items))
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

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item = request.json
    cart = session.get('cart', [])
    cart.append(item)
    session['cart'] = cart
    return jsonify({"message": "Item added to cart!"})

@app.route('/cart/<table_number>')
def cart(table_number):
    return render_template('cart.html', table_number=table_number)
    
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get all orders from the database
    orders = list(orders_collection.find().sort('created_at', -1))
    
    # Convert ObjectId to string
    for order in orders:
        order['_id'] = str(order['_id'])
    
    return render_template('admin.html', orders=orders)
    
@app.route('/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

        data = request.get_json() 
        order_id = data.get('order_id')
        new_status = data.get('status')

        if not order_id or not new_status:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # Convert string order_id to ObjectId
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404

        # Generate token number if status is changing to preparing
        token_number = None
        if new_status == 'preparing' and order.get('status') != 'preparing':
            # Generate a unique 2-digit token number
            while True:
                token_number = random.randint(10, 99)
                # Check if token number is already in use
                existing_order = orders_collection.find_one({'token_number': token_number})
                if not existing_order:
                    break

        # Update order status and token number
        update_data = {'status': new_status}
        if token_number:
            update_data['token_number'] = token_number

        result = orders_collection.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': update_data}
        )

        if result.modified_count > 0:
            # Send SMS notification
            if order.get('user_details', {}).get('mobile'):
                mobile = order['user_details']['mobile']
                print(f"Attempting to send SMS to: {mobile}")  # Debug log
                message = f"Your order {order.get('order_id', '')} status has been updated to {new_status}."
                if token_number:
                    message += f" Your token number is {token_number}."
                
                # Try to send SMS, but don't fail the request if SMS fails
                sms_sent = send_status_update_sms(mobile, message)
                if not sms_sent:
                    print("SMS notification failed, but order status was updated successfully")
            
            return jsonify({
                'success': True, 
                'message': 'Order status updated successfully',
                'token_number': token_number
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to update order status'}), 500

    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        return jsonify({'success': False, 'message': 'Error updating order status'}), 500

@app.route('/delete_order/<order_id>', methods=['POST'])
def delete_order(order_id):
    try:
        # Delete the order from MongoDB
        result = orders_collection.delete_one({'_id': ObjectId(order_id)})
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Order deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Order not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    try:
        # Get all orders and sort by creation date
        all_orders = list(orders_collection.find().sort('created_at', -1))
        
        # Convert ObjectId to string for JSON serialization
        for order in all_orders:
            order['_id'] = str(order['_id'])
            if 'user_id' in order:
                order['user_id'] = str(order['user_id'])
        
        return jsonify({
            'success': True, 
            'orders': all_orders
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
        if teacher_data:
            user = User()
            user.id = str(teacher_data['_id'])
            login_user(user)
            session['role'] = 'teacher'
            return redirect(url_for('menu', table_number=1))
        else:
            flash('Invalid teacher credentials', 'error')

    return render_template('teacher_login.html')

@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        items = data.get('items', [])
        total_amount = data.get('total_amount', 0)
        table_number = data.get('table_number')

        if not items or not table_number:
            return jsonify({'success': False, 'error': 'Missing required fields'})

        # Generate a unique order ID
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"

        # Get user details if user is logged in
        user_details = {}
        if current_user.is_authenticated:
            user_data = db.Users.find_one({"_id": ObjectId(current_user.id)})
            if user_data:
                user_details = {
                    'user_id': str(user_data['_id']),
                    'username': user_data['username'],
                    'mobile': user_data.get('mobile', ''),
                    'role': user_data.get('role', 'student')
                }

        # Create order document with user details
        order = {
            'order_id': order_id,
            'items': items,
            'total_amount': total_amount,
            'table_number': table_number,
            'status': 'pending',
            'created_at': datetime.now(),
            'user_details': user_details
        }

        # Insert order into database
        orders_collection.insert_one(order)

        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Order created successfully'
        })

    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create order'
        })

# Add Order and OrderItem models for MongoDB
class Order:
    def __init__(self, user_id, table_number, total_amount, order_id, status='pending'):
        self.user_id = user_id
        self.table_number = table_number
        self.total_amount = total_amount
        self.order_id = order_id
        self.status = status
        self.created_at = datetime.now()
        self.items = []

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'table_number': self.table_number,
            'total_amount': self.total_amount,
            'order_id': self.order_id,
            'status': self.status,
            'created_at': self.created_at,
            'items': self.items
        }

class OrderItem:
    def __init__(self, item_name, quantity, price):
        self.item_name = item_name
        self.quantity = quantity
        self.price = price

    def to_dict(self):
        return {
            'item_name': self.item_name,
            'quantity': self.quantity,
            'price': self.price
        }

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Remove the SQLAlchemy-style MenuItem model and replace with MongoDB document structure
def create_menu_item(name, price, category, description, image_path):
    return {
        'name': name,
        'price': price,
        'category': category,
        'description': description,
        'image_path': image_path,
        'created_at': datetime.utcnow()
    }

@app.route('/admin/add-menu-item', methods=['GET', 'POST'])
@login_required
def add_menu_item():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        description = request.form.get('description')
        
        # Handle image upload
        if 'image' not in request.files:
            flash('No image file uploaded', 'error')
            return redirect(request.url)
            
        file = request.files['image']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to make it unique
            filename = f"{int(time.time())}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Create new menu item using MongoDB
            new_item = create_menu_item(
                name=name,
                price=price,
                category=category,
                description=description,
                image_path=f'/static/images/menu_items/{filename}'
            )
            db.menu_items.insert_one(new_item)
            
            flash('Menu item added successfully!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid file type', 'error')
            return redirect(request.url)
    
    return render_template('add_menu_item.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            mobile = request.form.get('mobile')
            department = request.form.get('department')
            enrollment = request.form.get('enrollment')
            role = request.form.get('role')

            # Validate required fields
            if not username or not password or not mobile:
                return jsonify({
                    'success': False,
                    'message': 'Please fill in all required fields.'
                })

            # Format mobile number
            mobile = ''.join(filter(str.isdigit, mobile))
            if len(mobile) != 10:
                return jsonify({
                    'success': False,
                    'message': 'Please enter a valid 10-digit Indian mobile number.'
                })
            mobile = '+91' + mobile

            # Check if username already exists
            existing_user = db.Users.find_one({'username': username})
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': 'Username already exists. Please choose another.'
                })

            # Create new user document
            user = {
                'username': username,
                'password': password,  # In production, hash the password
                'mobile': mobile,
                'department': department if department else None,
                'enrollment': enrollment if enrollment else None,
                'role': role
            }

            # Insert user into database
            result = db.Users.insert_one(user)
            
            if result.inserted_id:
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! Click the Login button below to continue.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Registration failed. Please try again.'
                })

        except Exception as e:
            print(f"Error during signup: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'An error occurred during registration. Please try again.'
            })

    return render_template('signup.html')

@app.route('/clear_flash', methods=['POST'])
def clear_flash():
    session.pop('flash_message', None)
    session.pop('flash_category', None)
    return jsonify({'success': True})

@app.route('/admin/view-menu-items')
@login_required
def view_menu_items():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get all menu items from the database
    menu_items = list(db.menu_items.find())
    
    # Convert ObjectId to string for JSON serialization
    for item in menu_items:
        item['_id'] = str(item['_id'])
    
    return render_template('view_menu_items.html', menu_items=menu_items)

@app.route('/admin/delete-menu-item/<item_id>', methods=['POST'])
@login_required
def delete_menu_item(item_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Delete the menu item from MongoDB
        result = db.menu_items.delete_one({'_id': ObjectId(item_id)})
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Menu item deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Menu item not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/edit-menu-item/<item_id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(item_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get the menu item from database
    menu_item = db.menu_items.find_one({'_id': ObjectId(item_id)})
    if not menu_item:
        flash('Menu item not found.', 'error')
        return redirect(url_for('view_menu_items'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            price = float(request.form.get('price'))
            category = request.form.get('category')
            description = request.form.get('description')
            
            # Handle image upload if a new image is provided
            image_path = menu_item.get('image_path', '/static/images/default-food.jpg')
            if 'image' in request.files:
                file = request.files['image']
                if file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"{int(time.time())}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_path = f'/static/images/menu_items/{filename}'
            
            # Update menu item in database
            db.menu_items.update_one(
                {'_id': ObjectId(item_id)},
                {'$set': {
                    'name': name,
                    'price': price,
                    'category': category,
                    'description': description,
                    'image_path': image_path
                }}
            )
            
            flash('Menu item updated successfully!', 'success')
            return redirect(url_for('view_menu_items'))
            
        except Exception as e:
            flash(f'Error updating menu item: {str(e)}', 'error')
    
    return render_template('edit_menu_item.html', menu_item=menu_item)

@app.route('/get_order_details/<order_id>', methods=['GET'])
@login_required
def get_order_details(order_id):
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

        # Convert string order_id to ObjectId
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404

        # Convert ObjectId to string for JSON serialization
        order['_id'] = str(order['_id'])
        
        return jsonify({'success': True, 'order': order})
    except Exception as e:
        print(f"Error fetching order details: {str(e)}")
        return jsonify({'success': False, 'message': 'Error fetching order details'}), 500

@app.route('/get_user_orders')
@login_required
def get_user_orders():
    try:
        # Get all orders for the current user that are not delivered
        orders = list(orders_collection.find({
            'user_details.user_id': str(current_user.id)
        }).sort('created_at', -1))
        
        # Convert ObjectId to string for JSON serialization
        for order in orders:
            order['_id'] = str(order['_id'])
        
        return jsonify({
            'success': True,
            'orders': orders
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

def send_status_update_sms(mobile, message):
    try:
        # Check if Twilio credentials are available
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            print("Twilio credentials not configured")
            return False

        # Format mobile number
        # Remove any non-digit characters
        mobile = ''.join(filter(str.isdigit, mobile))
        
        # Handle numbers that might already have 91 prefix
        if mobile.startswith('91') and len(mobile) == 12:
            mobile = mobile[2:]  # Remove 91 prefix if present
        elif len(mobile) != 10:
            print(f"Invalid mobile number format: {mobile}")
            return False
            
        # Add +91 prefix
        mobile = '+91' + mobile

        print(f"Sending SMS to formatted number: {mobile}")  # Debug log

        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        try:
            # Send SMS
            message = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=mobile
            )
            print(f"SMS sent successfully to {mobile}")
            return True
        except Exception as e:
            error_message = str(e)
            if "unverified" in error_message.lower():
                print(f"Twilio Error: Phone number {mobile} needs to be verified in your Twilio account.")
                print("Please visit https://www.twilio.com/console/phone-numbers/verified to verify your number.")
                print("This is required for trial accounts. Once verified, SMS will work automatically.")
            else:
                print(f"Error sending SMS: {error_message}")
            return False

    except Exception as e:
        print(f"Error in SMS function: {str(e)}")
        return False

@app.route('/order_details/<order_id>')
@login_required
def order_details(order_id):
    if current_user.role != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    try:
        print(f"Fetching order details for ID: {order_id}")  # Debug log
        order = orders_collection.find_one({'_id': ObjectId(order_id)})
        if not order:
            print(f"Order not found for ID: {order_id}")  # Debug log
            flash('Order not found', 'error')
            return redirect(url_for('admin'))
        
        # Convert ObjectId to string for template rendering
        order['_id'] = str(order['_id'])
        
        # Ensure all required fields are present
        if 'items' not in order:
            order['items'] = []
        if 'user_details' not in order:
            order['user_details'] = {
                'user_id': 'N/A',
                'username': 'Guest',
                'mobile': 'N/A',
                'role': 'guest'
            }
        if 'total_amount' not in order:
            order['total_amount'] = 0
        if 'status' not in order:
            order['status'] = 'pending'
        if 'token_number' not in order:
            order['token_number'] = None
        if 'created_at' not in order:
            order['created_at'] = datetime.now()
            
        print(f"Order data prepared for template: {order}")  # Debug log
        return render_template('order_details.html', order=order)
    except Exception as e:
        print(f"Error fetching order details: {str(e)}")  # Debug log
        flash('Error fetching order details', 'error')
        return redirect(url_for('admin'))

@app.route('/create_payment', methods=['POST'])
@login_required
def create_payment():
    try:
        data = request.get_json()
        cart_items = data.get('items', [])
        table_number = data.get('table_number')
        total_amount = data.get('total_amount', 0)
        
        print(f"Creating payment for amount: {total_amount}")  # Debug log
        
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Create Razorpay order
        order_amount = int(total_amount * 100)  # Convert to paise
        order_currency = 'INR'
        order_receipt = f'order_rcpt_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        
        # Create order with additional parameters
        order = razorpay_client.order.create({
            'amount': order_amount,
            'currency': order_currency,
            'receipt': order_receipt,
            'payment_capture': 1,
            'notes': {
                'table_number': table_number,
                'user_id': str(current_user.id)
            }
        })
        
        print(f"Created Razorpay order: {order}")  # Debug log
        
        return jsonify({
            'order_id': order['id'],
            'amount': order_amount,
            'currency': order_currency,
            'key': RAZORPAY_KEY_ID,
            'name': 'TableTreats',
            'description': 'Order Payment',
            'prefill': {
                'name': current_user.username,
                'email': current_user.email if hasattr(current_user, 'email') else '',
                'contact': current_user.mobile if hasattr(current_user, 'mobile') else ''
            },
            'theme': {
                'color': '#3399cc'
            },
            'test': True  # Explicitly set test mode
        })
    except Exception as e:
        print(f"Error creating payment: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500

@app.route('/payment_success', methods=['GET', 'POST'])
@login_required
def payment_success():
    try:
        if request.method == 'POST':
            # Get payment details from form
            razorpay_payment_id = request.form.get('razorpay_payment_id')
            razorpay_order_id = request.form.get('razorpay_order_id')
            razorpay_signature = request.form.get('razorpay_signature')
            
            print(f"Payment success received - Payment ID: {razorpay_payment_id}")  # Debug log
            
            # Verify payment signature
            params_dict = {
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_order_id': razorpay_order_id,
                'razorpay_signature': razorpay_signature
            }
            
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Get cart items from the request data
            cart_items = request.form.getlist('cart_items[]')
            if not cart_items:
                return jsonify({'success': False, 'message': 'No items in cart'}), 400
            
            # Parse cart items from JSON
            try:
                cart_items = [json.loads(item) for item in cart_items]
            except json.JSONDecodeError:
                return jsonify({'success': False, 'message': 'Invalid cart items format'}), 400
            
            # Calculate total amount
            total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
            total_amount_with_gst = total_amount * 1.05  # Adding 5% GST
            
            # Generate a unique order ID
            order_id = f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}'
            
            # Get user details
            user_data = db.Users.find_one({"_id": ObjectId(current_user.id)})
            user_details = {
                'username': user_data.get('username', ''),
                'mobile': user_data.get('mobile', ''),
                'role': user_data.get('role', 'student')
            }
            
            # Create order in database
            order_data = {
                'order_id': order_id,
                'user_id': str(current_user.id),
                'items': cart_items,
                'total_amount': total_amount_with_gst,
                'payment_id': razorpay_payment_id,
                'status': 'pending',
                'created_at': datetime.now(),
                'table_number': request.form.get('table_number'),
                'user_details': user_details
            }
            
            # Insert order into database
            result = orders_collection.insert_one(order_data)
            print(f"Order created in database with ID: {result.inserted_id}")  # Debug log
            
            # Return success response with order ID
            return jsonify({
                'success': True,
                'message': 'Order placed successfully!',
                'order_id': order_id
            })
            
        else:
            # Handle GET request
            return redirect(url_for('menu', table_number=session.get('table_number', 1)))
            
    except Exception as e:
        print(f"Error in payment success: {str(e)}")  # Debug log
        return jsonify({
            'success': False,
            'message': 'Payment verification failed. Please try again.'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)

