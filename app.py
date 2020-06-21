import os

from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from models import goodreads

app = Flask(__name__)


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine("postgres://vhekodilfwzsko:e011eb44281d36e038d50ef410233f2d4454512b3b53953a89d84a8eb1a9a51a@ec2-52-200-48-116.compute-1.amazonaws.com:5432/d3ifvajs6ao258")
db = scoped_session(sessionmaker(bind=engine))


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    if request.method == "POST":
        book = "%" + request.form.get("book") + "%"
        book = book.title()
        rows = db.execute("""SELECT * FROM books WHERE isbn LIKE :book OR title
                          LIKE :book OR author LIKE :book""",
                          {"book": book}).fetchall()
        if len(rows) < 1:
            error = "No Book with that ISBN/Title/Author/Year!"
            return render_template("error.html", error=error)
        else:
            return render_template("books.html", rows=rows)
    else:
        return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": username}).fetchall()

        if len(rows) != 1:
            flash('Account does not exist, please register!')
            return render_template("register.html")
        elif not check_password_hash(rows[0]["hash"], password):
            flash('Invalid username/password')
            return render_template("login.html")

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        email = request.form.get("email")

        user = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": username}).fetchall()
        em = db.execute("SELECT * FROM users WHERE email = :email",
                        {"email": email}).fetchall()

        if len(user) == 1:
            flash('Usename taken already')
            return render_template("register.html")
        if len(em) == 1:
            flash('An account with this email already exists, please log in!')
            return render_template("login.html")

        if password == request.form.get("re-password"):
            # Query database for username
            hashp = generate_password_hash(password, method='pbkdf2:sha256',
                                           salt_length=8)
            db.execute("""INSERT INTO users(username, hash, fname, lname, email)
                       VALUES (:username, :hashp, :fname, :lname, :email)""",
                       {"username": username, "hashp": hashp, "fname": fname,
                        "lname": lname, "email": email})
            db.commit()
            # Redirect user to home page
            flash('Registration Succesful!')
            return render_template("login.html")
        else:
            flash('Passwords must match')
            return render_template("register.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    flash('Logged out!')
    return render_template("login.html")


@app.route("/book_info/<isbn>", methods=["GET", "POST"])
@login_required
def book_info(isbn):
    isbn = isbn
    user_id = session["user_id"]
    if request.method == "GET":
        gr_ratings = goodreads(isbn)
        rows = db.execute("""SELECT * FROM books WHERE isbn LIKE :isbn""",
                          {"isbn": isbn}).fetchall()
        review = db.execute("""SELECT * FROM reviews WHERE user_id=:user_id
                            AND book_id LIKE :isbn""",
                            {"user_id": user_id, "isbn": isbn}).fetchall()
        reviews = db.execute("""SELECT rating, comment, fname FROM reviews
                             JOIN users ON reviews.user_id=users.id
                             WHERE book_id LIKE :isbn""",
                             {"isbn": isbn}).fetchall()
        submit = 0
        r = 1
        if len(review) > 0:
            submit = 1
        if len(reviews) == 0:
            r = 0
        return render_template("bookinfo.html", rows=rows, submit=submit,
                               reviews=reviews, isbn=isbn, r=r,
                               gr_ratings=gr_ratings)
    else:
        review = request.form.get("review")
        rating = request.form.get("rating")
        db.execute("""INSERT INTO reviews(rating, comment, book_id, user_id)
                    VALUES(:rating, :comment, :isbn, :user_id)""",
                   {"rating": rating, "comment": review, "isbn": isbn,
                    "user_id": user_id})
        db.commit()
        flash('Review Submitted!')
        return redirect("/book_info/"+isbn)


@app.route("/api/<isbn>")
def api(isbn):
    book = db.execute("""SELECT title, author, year, isbn FROM books
                      WHERE isbn LIKE :isbn""",
                      {"isbn": isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Invalid ISBN"}), 404
    gr_ratings = goodreads(isbn)
    review_count = gr_ratings['n_ratings']
    average_score = gr_ratings['avg_rating']
    return jsonify({
            "title": book['title'],
            "author": book['author'],
            "year": book['year'],
            "isbn": book['isbn'],
            "review_count": review_count,
            "average_score": average_score
    })


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
