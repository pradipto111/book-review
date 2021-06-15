import requests
import os
import hashlib

def hash_string(string):
    """
    Return a SHA-256 hash of the given string
    """
    return hashlib.sha256(string.encode('utf-8')).hexdigest()

from flask import Flask, session, render_template, request, redirect, url_for, jsonify, make_response
from flask_session import Session   
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

activeid = 0

@app.route("/")
def index():
    return render_template("HomePage.html")

@app.route("/register")
def register():
    return render_template("Register.html")

@app.route("/Check", methods=["POST"])
def Check():
    rawpw1 = request.form.get("rawpw1")
    rawpw2 = request.form.get("rawpw2")
    if hash_string(rawpw1) != hash_string(rawpw2):
        return render_template("RegError.html", message="REGISTRATION FAILED")
    password = str(hash_string(rawpw1))
    name = request.form.get("name")
    db.execute("INSERT INTO users (name, password) VALUES(:name, :password)", 
    {"name":name, "password":password})
    db.commit()
    users=db.execute("SELECT uid, name, password FROM users WHERE password= :password", {"password":password})
    return render_template("RegSuccess.html", message="REGISTRATION SUCCESSFUL", users=users)

@app.route("/account", methods=["POST"])
def account():
    uid=request.form.get("logid")
    password=request.form.get("password")
    users = db.execute("SELECT uid, name, password FROM users WHERE uid = :uid", {"uid":uid})
    if users == None:
        return render_template("LogError.html", message = "LOG IN FAILED, none users")

    for user in users:
        name=user.name
        if str(hash_string(password)) != user.password:
            return render_template("LogError.html", message = "LOG IN FAILED, wrong password")
    
    global activeid
    activeid=uid

    return render_template("AccHome.html",name=name)

@app.route("/search", methods=["POST"])
def search():
    by = request.form.get("by")
    keyword = request.form.get("keyword")
    results=None
    if by == "byisbn":
        keyword = keyword + "%"
        results=db.execute("SELECT isbn, bookname, author, year FROM books WHERE isbn LIKE :keyword",
        {"keyword": keyword})

    if by=="bybookname":
        keyword = "%" + keyword + "%"
        results=db.execute("SELECT isbn, bookname, author, year FROM books WHERE bookname LIKE :keyword",
        {"keyword": keyword})

    if by=="byauthor":
        keyword = "%" + keyword + "%"
        results=db.execute("SELECT isbn, bookname, author, year FROM books WHERE author LIKE :keyword",
        {"keyword": keyword})

    if by=="byyear":
        results=db.execute("SELECT isbn, bookname, author, year FROM books WHERE year = :keyword",
        {"keyword": keyword})
    
    return render_template("SearchResults.html", results=results)

@app.route("/detail/<string:isbn>", methods=["POST"])
def detail(isbn):
    books= db.execute("SELECT isbn, bookname, author, year FROM books WHERE isbn = :isbn", {"isbn":isbn})
    for book in books:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", 
        params={"key": "bEoRa8J9pQSvGacWbP0IQ", "isbns": book.isbn})
        data = res.json()
        rate = data["books"][0]['average_rating']
        ratecount= data["books"][0]['work_ratings_count']
        reviewcount=data["books"][0]['work_reviews_count']
        reviews = db.execute("SELECT users.uid, isbn, review, rate, name FROM reviews, users WHERE isbn = :isbn AND users.uid = reviews.uid",
        {"isbn":book.isbn})
        return render_template("Details.html", book=book, rate=rate, ratecount=ratecount, reviewcount=reviewcount, reviews=reviews)

@app.route("/write/<string:isbn>", methods=["POST"])   
def write(isbn):
    books = db.execute("SELECT isbn, bookname, author, year FROM books WHERE isbn = :isbn", {"isbn":isbn})
    for book in books:
        return render_template("Write.html", book=book)

@app.route("/submit/<string:isbn>", methods=["POST"])
def submit(isbn):
    books = db.execute("SELECT isbn, bookname, author, year FROM books WHERE isbn = :isbn", {"isbn":isbn})
    for book in books:
        review = request.form.get("review")  
        rate=request.form.get("rate")
        db.execute("INSERT INTO reviews(uid, isbn, review, rate) VALUES(:uid, :isbn, :review, :rate)",
        {"uid":activeid, "isbn":book.isbn, "review":review, "rate":rate})
        db.commit()
        return render_template("SubmitSuccess.html", message = "REVIEW SUBMITTED")

@app.route("/logout", methods=["POST"])
def logout():
    global activeid
    activeid=0
    return redirect(url_for('index'))



@app.route("/api/<string:isbn>", methods=["GET", "POST"])
def api(isbn):
    #books = db.execute("SELECT bookname, author, year FROM books WHERE isbn = :isbn", {"isbn":isbn})
    #for book in books:
    #    avg = db.execute("SELECT AVG(rate) FROM reviews WHERE isbn = :isbn", {"isbn":isbn})
   #     count = db.execute("SELECT COUNT(review) FROM reviews WHERE isbn = :isbn", {"isbn":isbn})
          #return jsonify([1,2,3])
    #    return jsonify([isbn])
    I = db.execute("SELECT COUNT(review) FROM reviews WHERE isbn=:isbn", {"isbn":isbn}).fetchall()
    avgs = db.execute("SELECT AVG(rate) FROM reviews WHERE isbn=:isbn", {"isbn":isbn}).fetchall()
    for bit in I:
            #i = bit[0]
        i = str((bit[0]))
    for bit in avgs:
        avg = str(bit[0])

    books = db.execute("SELECT bookname, author, year FROM books WHERE isbn=:isbn", {"isbn":isbn})
    for bit in books:
        title  = str(bit.bookname)
        author = str(bit.author)
        year = str(bit.year)
    return jsonify({
        "isbn": isbn,
        "title":title,
        "author": author,
        "year_of_publish": year,
        "review_count":i,
        "average_rating": avg
    })
        

@app.route("/account1", methods=["POST"])
def account_():
    #global activeid
    users = db.execute("SELECT name, password FROM users WHERE uid = :activeid", {"activeid":activeid})
    for user in users:
        #return render_template("AccHome.html", name = user.name)
        return render_template("AccHome.html", name = user.name)
''