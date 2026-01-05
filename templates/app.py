from flask import Flask, render_template, redirect, session
import stripe
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "harikala_secret_key"

# ===============================
# STRIPE TEST MODE
# ===============================
stripe.api_key = "sk_test_51Sm7gi5Gp59w9Uclk6fF1Kkr5cfDMdE68hcSsTYEhKpZZHZWZBdKQn36aIdFlRW3E1TNxxwQLs2RMjlx7fRfA9hf00BN59L7u1"
STRIPE_PUBLISHABLE_KEY = "pk_test_51Sm7gi5Gp59w9UclRtMUEokDwsc7DMT0PPOz0N3zgaCoNJz3YS5pA6uHFvdyBANO5IkaZumEoTNGreEHW6afNaY100xS6hWtpK"

# ===============================
# PRODUCTS
# ===============================
products = [
    {"id": 1, "name": "Phenyl – Rose Fragrance", "price": 120},
    {"id": 2, "name": "Phenyl – Lemon Fragrance", "price": 115},
    {"id": 3, "name": "Phenyl – Lavender Fragrance", "price": 130},
    {"id": 4, "name": "Phenyl – Pine Fragrance", "price": 125},
    {"id": 5, "name": "Cleaning Acid", "price": 90},
    {"id": 6, "name": "Distilled Water (5 Litres)", "price": 70},
]

ORDER_STATUSES = [
    "Order Received",
    "Shipped",
    "In Transit",
    "Out for Delivery"
]

# ===============================
# SAFETY: FIX BROKEN SESSION
# ===============================
@app.before_request
def fix_session():
    if not isinstance(session.get("cart", {}), dict):
        session["cart"] = {}
    if not isinstance(session.get("orders", []), list):
        session["orders"] = []

# ===============================
# BASIC PAGES
# ===============================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/products")
def product_page():
    return render_template("products.html", products=products)

# ===============================
# API CART (NO REDIRECT)
# ===============================
@app.route("/api/add-to-cart/<int:product_id>", methods=["POST"])
def api_add_to_cart(product_id):
    cart = session.get("cart", {})
    pid = str(product_id)
    cart[pid] = cart.get(pid, 0) + 1
    session["cart"] = cart
    return {"qty": cart[pid]}

@app.route("/api/update-cart/<int:product_id>/<action>", methods=["POST"])
def update_cart(product_id, action):
    cart = session.get("cart", {})
    pid = str(product_id)

    if pid not in cart:
        return {"qty": 0}

    if action == "increase":
        cart[pid] += 1
    elif action == "decrease":
        cart[pid] -= 1
        if cart[pid] <= 0:
            cart.pop(pid)

    session["cart"] = cart
    return {"qty": cart.get(pid, 0)}

# ===============================
# CART PAGE
# ===============================
@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    cart_items = []
    total = 0

    for p in products:
        pid = str(p["id"])
        if pid in cart:
            qty = cart[pid]
            subtotal = qty * p["price"]
            total += subtotal
            cart_items.append({
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "qty": qty,
                "subtotal": subtotal
            })

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total,
        stripe_key=STRIPE_PUBLISHABLE_KEY
    )

@app.route("/clear-cart")
def clear_cart():
    session["cart"] = {}
    return redirect("/products")

# ===============================
# STRIPE CHECKOUT
# ===============================
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    cart = session.get("cart", {})
    line_items = []
    paid_items = []
    total_amount = 0

    for p in products:
        pid = str(p["id"])
        if pid in cart:
            qty = cart[pid]
            paid_items.append(p["name"])
            total_amount += p["price"] * qty
            line_items.append({
                "price_data": {
                    "currency": "inr",
                    "product_data": {"name": p["name"]},
                    "unit_amount": p["price"] * 100,
                },
                "quantity": qty,
            })

    session["last_payment"] = {
        "amount": total_amount,
        "items": paid_items
    }

    checkout = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url="http://127.0.0.1:5000/success",
        cancel_url="http://127.0.0.1:5000/cancel",
    )

    return redirect(checkout.url)

# ===============================
# SUCCESS / ORDERS
# ===============================
@app.route("/success")
def success():
    summary = session.pop("last_payment", {"amount": 0, "items": []})
    order_id = str(uuid.uuid4())[:8].upper()

    orders = session.get("orders", [])
    orders.append({
        "order_id": order_id,
        "amount": summary["amount"],
        "items": summary["items"],
        "status_index": 0,
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p")
    })

    session["orders"] = orders
    session["cart"] = {}

    return render_template(
        "success.html",
        order_id=order_id,
        amount=summary["amount"],
        items=summary["items"],
        demo=True
    )

@app.route("/orders")
def orders():
    orders = session.get("orders", [])
    for o in orders:
        if o["status_index"] < len(ORDER_STATUSES) - 1:
            o["status_index"] += 1

    session["orders"] = orders
    return render_template("orders.html", orders=orders, statuses=ORDER_STATUSES)

@app.route("/cancel")
def cancel():
    return render_template("cancel.html")

if __name__ == "__main__":
    app.run(debug=True)
