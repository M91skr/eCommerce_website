from flask import Flask, render_template, request, url_for, redirect, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os

api_key = "API_KEY"
stripe.api_key = os.getenv(api_key)
YOUR_DOMAIN = 'http://localhost:5000'


app = Flask(__name__)

# Db connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'any-secret-key-you-choose'
db = SQLAlchemy(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    status = db.Column(db.String(250), nullable=False)


class Products(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    product_name = db.Column(db.String(250), nullable=False)
    category = db.Column(db.String(250), nullable=False)
    provider = db.Column(db.String(250), nullable=False)
    product_image = db.Column(db.String(500))


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product_price = db.Column(db.SmallInteger, nullable=False)
    count = db.Column(db.SmallInteger, nullable=False)
    product_name = db.relationship('Products')


@app.route("/")
def home():
    products_list = Products.query.all()
    return render_template("home.html", products=products_list)


@app.route('/images/<file_name>')
def image_path(file_name):
    return send_file(
        f'static/images/{file_name}',
        mimetype="image/jpeg",
        as_attachment=True)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(email=request.form.get('email')).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=hash_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", logged_in=current_user.is_authenticated)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/basket/")
@login_required
def cart():
    cart_list = Cart.query.all()
    selected_product = []
    selected_stock = []
    for item in cart_list:
        id = item.product_id
        product = Products.query.get(id)
        stock = Stock.query.get(item.product_id)
        selected_product.append(product)
        selected_stock.append(stock)
    return render_template("cart.html", selected=zip(selected_product, selected_stock), name=current_user.name, logged_in=True)


@app.route("/add_item/<product_id>", methods=["GET", "POST"])
@login_required
def add_item(product_id):
    cart = Cart(
        user_id=current_user.id,
        product_id= product_id,
        status="ADD_TO_CART"
    )
    db.session.add(cart)
    db.session.commit()
    return redirect(url_for("cart", product_id=product_id))


@app.route("/payment/<price>", methods=['POST'])
def pay(price):
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': f'{price}',
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '/success.html',
            cancel_url=YOUR_DOMAIN + '/cancel.html',
            )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


if __name__ == '__main__':
    app.run(debug=True)
