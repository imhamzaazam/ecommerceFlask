from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from passlib.apps import custom_app_context as pwd_context
from helpers import apology, login_required, lookup, usd
import os
# Configure application
app = Flask(__name__)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///ecommDb.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    name = db.execute("select username, cash from users where id = :id ", id = session["user_id"])
    rows = db.execute("select * from cart where user_id = :id", id=session["user_id"])
    invi = db.execute("select * from invoice where user_id = :id", id=session["user_id"])
    count=0
    for purchase in invi:
        count+=purchase["total"]
    return render_template("index.html", items=rows , name=name , invi=invi, count=count)
    #return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        product = request.form.get("product")
        rows = db.execute("Select * from products where product_name= :name", name = product)
        if not rows[0]["product_name"]:
            return apology("Product does not exists")
        quantity= int(request.form.get("quantity"))
        if quantity<0:
            return apology("Enter valid quantity")
        if (quantity > rows[0]["product_stock"]):
            return apology("Stock not available")
        else:
            cash = db.execute("Select cash from users where id=:id", id=session["user_id"])
            if not cash or float(cash[0]["cash"] < float(rows[0]["product_price"])):
                return apology("Not enough cash")
        db.execute("Update users set cash = cash - :bought where id = :id", bought= rows[0]["product_price"], id=session["user_id"])
        flash('Bought')
        db.execute("insert into invoice(inv_date, total, product_id, user_id) values (datetime('now', 'localtime'), :total, :p_id, :id)", total =  rows[0]["product_price"], p_id=rows[0]["product_id"], id=session["user_id"])

        db.execute("Update products set product_stock = product_stock - :count where product_name=:name", name=product, count=quantity)
        return redirect(url_for("index"))
    else:
        return render_template("buy.html")



@app.route("/category", methods=["GET", "POST"])
@login_required
def category():
    rows = db.execute("SELECT * FROM category")
    return render_template("category.html", categ=rows)

@app.route("/addProducts", methods=["GET", "POST"])
@login_required
def addProducts():
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("product"):
            return apology("must provide product", 403)
        if not request.form.get("price"):
            return apology("must provide price", 403)
        if not request.form.get("stock"):
            return apology("must provide stock", 403)


        target = os.path.join(APP_ROOT, 'static/')
        print(target)

        if not os.path.isdir(target):
            os.mkdir(target)

        for file in request.files.getlist("file"):
            print(file)
            filename = file.filename
            destination='/'.join([target, filename])
            print(destination)
            file.save(destination)

        db.execute("insert into category(category_id, category_name) values (:cid, :cname)", cid=request.form.get("cid"), cname=request.form.get("category"))
        db.execute("insert into products (product_name, product_price, product_stock, category_id) values (:name \
        ,:price, :stock, :cid)", name=request.form.get("product"),
        price=request.form.get("price"), stock=request.form.get("stock"), cid=request.form.get("cid"))
        flash("Product added")
        return render_template("addProducts.html")
    else:
        return render_template("addProducts.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not rows[0]["hash"] == request.form.get("password"):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/cart", methods=["GET", "POST"])
@login_required
def cart():
    if request.method == "GET":
        rows = db.execute("select * from cart where user_id = :id", id=session["user_id"])
        return render_template("cart.html", items=rows)
    else:
        rows = db.execute("select * from cart where user_id = :id", id=session["user_id"])
        for item in rows:

            prod = db.execute("select * from products where product_id= :id", id = item["product_id"])
            if int((prod[0]["product_stock"])) < 1:
                return apology("Stock Finished")
            cash = db.execute("Select cash from users where id=:id", id=session["user_id"])
            if not cash or float(cash[0]["cash"] < float(prod[0]["product_price"])):
                return apology("Not enough cash")
            db.execute("Update users set cash = cash - :bought where id = :id", bought= float(prod[0]["product_price"] * item["quantity"]) , id=session["user_id"])
            flash('Bought')
            db.execute("insert into invoice(inv_date, total, product_id, user_id) values (datetime('now', 'localtime'), :total, :p_id, :id)", total =  prod[0]["product_price"]* item["quantity"], p_id=prod[0]["product_id"], id=session["user_id"])
            db.execute("Update products set product_stock = product_stock - :count where product_name=:name", count=item["quantity"], name = prod[0]["product_name"] )
            db.execute("Delete from cart where user_id = :id", id=session["user_id"])
        return render_template("cart.html")
@app.route("/product", methods=["GET", "POST"])
@login_required
def product():
    """Get stock quote."""
    if request.method == "GET":
        rows = db.execute("SELECT * FROM products")
        arg1 = int(request.args['arg1'])
        if (arg1 != 0):
            cartItem = db.execute("SELECT quantity FROM cart \
                           WHERE user_id = :id AND product_id=:symbol", \
                           id=session["user_id"], symbol=arg1)
            if not cartItem:
                db.execute("INSERT INTO cart (quantity, product_id, user_id) VALUES (1 ,:product_id, :user_id)", product_id = arg1, user_id=session["user_id"])
                flash("item added to cart")
            else:
                cartItem[0]["quantity"] = cartItem[0]["quantity"] + 1
                db.execute("update cart set quantity=:quantity where product_id= :product_id and user_id = :id", quantity=cartItem[0]["quantity"], product_id = arg1, id=session["user_id"])
                flash("item added to cart")
        return render_template("product.html", abc=rows)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
      # ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password")

        # ensure password and verified password is the same
        elif request.form.get("password") != request.form.get("passwordagain"):
            return apology("password doesn't match")

        elif not request.form.get("contact"):
            return apology("Must provide Contact")
        elif not request.form.get("address"):
            return apology("Must provide Address")
        elif not request.form.get("cash"):
            return apology("Must provide cash")

        # insert the new user into users, storing the hash of the user's password
        result = db.execute("INSERT INTO users (username, hash, cash, contact_number, address) VALUES(:username, :hash, :cash, :contact_number, :address)",
                            username=request.form.get("username"),
                            hash=request.form.get("password"),
                            cash=request.form.get("cash"),
                            contact_number= request.form.get("contact"),
                            address=request.form.get("address")
                            )

        if not result:
            return apology("Username already exist")

        # remember which user has logged in
        session["user_id"] = result

        # redirect user to home page
        return redirect(url_for("index"))

    else:
        return render_template("register.html")






def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
