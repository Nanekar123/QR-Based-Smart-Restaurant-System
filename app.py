import razorpay
from flask import Flask, render_template, request, redirect, session, jsonify
from db import get_db_connection
import jwt, datetime, random
from flask_mail import Mail, Message
import os

app = Flask(__name__, static_folder='utils/static')
app.secret_key = "supersecret"

JWT_SECRET = "jwt_secret"

# ================= MAIL =================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'supriyananekar91@gmail.com'
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = True

mail = Mail(app)

# ================= AUTH =================
def check_auth():
    token = session.get('access_token')
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except:
        return None

# =====================================================
# CUSTOMER
# =====================================================

@app.route('/')
def home():
    return render_template('customer/welcome.html')

@app.route('/menu')
def menu():
    # ✅ keep existing table_no if already in session
    table_no = request.args.get('table') or session.get('table_no')

    if table_no:
        session['table_no'] = table_no

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu")
    menu_items = cursor.fetchall()
    conn.close()

    return render_template('customer/menu.html', menu_items=menu_items)
    
@app.route('/add_to_cart/<int:item_id>')
def add_to_cart(item_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu WHERE id=%s", (item_id,))
    item = cursor.fetchone()
    conn.close()

    cart = session.get('cart', {})

    if item:
        name = item['name']
        cart.setdefault(name, {'price': item['price'], 'qty': 0})
        cart[name]['qty'] += 1

    session['cart'] = cart
    return redirect('/menu')

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    total = sum(i['price'] * i['qty'] for i in cart.values())
    return render_template('customer/cart.html', cart=cart, total=total)

# =====================================================
# CHECKOUT
# =====================================================

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    total = sum(i['price'] * i['qty'] for i in cart.values())
    table_no = session.get('table_no')

    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()

        order_id = session.get('order_id')

        if order_id:
            for name, item in cart.items():
                cursor.execute(
                    "INSERT INTO order_items (order_id, item_name, price, quantity) VALUES (%s,%s,%s,%s)",
                    (order_id, name, item['price'], item['qty'])
                )

            cursor.execute(
                "UPDATE orders SET total = total + %s WHERE id=%s",
                (total, order_id)
            )
        else:
            cursor.execute(
                "INSERT INTO orders (table_no, total, status) VALUES (%s,%s,%s)",
                (table_no, total, 'Running')
            )
            order_id = cursor.lastrowid

            for name, item in cart.items():
                cursor.execute(
                    "INSERT INTO order_items (order_id, item_name, price, quantity) VALUES (%s,%s,%s,%s)",
                    (order_id, name, item['price'], item['qty'])
                )

        conn.commit()
        conn.close()

        session['order_id'] = order_id
        session['cart'] = {}

        return render_template('customer/order_placed.html', order_id=order_id)

    return render_template('customer/checkout.html', cart=cart, total=total, table_no=table_no)

# =====================================================
# ORDER TRACKING
# =====================================================

@app.route('/order_status')
def order_status():
    order_id = session.get('order_id')

    if not order_id:
        return redirect('/menu')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    items = cursor.fetchall()

    conn.close()

    return render_template('customer/order_status.html', order=order, items=items)

# =====================================================
# FINAL BILL
# =====================================================

@app.route('/final_bill')
def final_bill():
    order_id = session.get('order_id')

    if not order_id:
        return redirect('/menu')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()

    cursor.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    items = cursor.fetchall()

    conn.close()

    return render_template('customer/final_bill.html', order=order, items=items)

# =====================================================
# PAYMENT
# =====================================================

@app.route('/payment', methods=['POST'])
def payment():
    order_id = session.get('order_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()

    method = request.form['payment_method']

    cursor.execute(
        "INSERT INTO payments (order_id, payment_method, amount, status) VALUES (%s,%s,%s,%s)",
        (order_id, method, order['total'], 'Success')
    )

    cursor.execute("UPDATE orders SET status='Paid' WHERE id=%s", (order_id,))

    conn.commit()
    conn.close()

    session.clear()

    return render_template('customer/payment_success.html',
                           order_id=order_id,
                           amount=order['total'],
                           method=method)

# =====================================================
# ADMIN
# =====================================================

@app.route('/admin/login')
def login():
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')

# =====================================================

if __name__ == "__main__":
    app.run(debug=True)