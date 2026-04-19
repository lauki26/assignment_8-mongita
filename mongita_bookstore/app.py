from flask import Flask, render_template, request, redirect, url_for
from mongita import MongitaClientDisk
import os

app = Flask(__name__)

# ------------------------------------------
# Mongita Setup (local embedded NoSQL DB)
# ------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
client = MongitaClientDisk(os.path.join(BASE_DIR, "mongita_data"))

db = client.bookstore
categories_col = db.category
books_col = db.book


# ------------------------------------------
# Helper Functions
# ------------------------------------------
def get_categories():
    categories = list(categories_col.find())
    return sorted(categories, key=lambda c: c["categoryName"])


def get_next_book_id():
    books = list(books_col.find())

    if not books:
        return 1

    return max(book["bookId"] for book in books) + 1


# ------------------------------------------
# HOME PAGE
# ------------------------------------------
@app.route("/", methods=["GET"])
def home():
    categories = get_categories()
    return render_template("index.html", categories=categories)


# ------------------------------------------
# CATEGORY PAGE
# /category?categoryId=1
# ------------------------------------------
@app.route("/category", methods=["GET"])
def category():
    category_id = request.args.get("categoryId", type=int)

    categories = get_categories()
    selected_category = categories_col.find_one({"categoryId": category_id})

    books = list(books_col.find({"categoryId": category_id}))
    books = sorted(books, key=lambda b: b["title"])

    return render_template(
        "category.html",
        categories=categories,
        selectedCategory=selected_category,
        books=books,
        searchTerm=None,
        nothingFound=False
    )


# ------------------------------------------
# SEARCH
# ------------------------------------------
@app.route("/search", methods=["POST"])
def search():
    term = request.form.get("search", "").strip()

    categories = get_categories()
    all_books = list(books_col.find())

    books = [
        book for book in all_books
        if term.lower() in book["title"].lower()
    ]
    books = sorted(books, key=lambda b: b["title"])

    return render_template(
        "category.html",
        categories=categories,
        selectedCategory=None,
        books=books,
        searchTerm=term,
        nothingFound=(len(books) == 0)
    )


# ------------------------------------------
# BOOK DETAIL PAGE
# /book?bookId=3
# ------------------------------------------
@app.route("/book", methods=["GET"])
def book_detail():
    book_id = request.args.get("bookId", type=int)

    categories = get_categories()
    book = books_col.find_one({"bookId": book_id})

    if not book:
        return render_template("error.html", error="Book not found"), 404

    return render_template(
        "book_detail.html",
        book=book,
        categories=categories
    )


# ------------------------------------------
# ADD BOOK
# ------------------------------------------
@app.route("/add-book", methods=["GET", "POST"])
def add_book():
    categories = get_categories()

    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        isbn = request.form.get("isbn")
        price = request.form.get("price", type=float)
        image = request.form.get("image")
        category_id = request.form.get("categoryId", type=int)

        selected_category = next(
            (c for c in categories if c["categoryId"] == category_id),
            None
        )

        new_book = {
            "bookId": get_next_book_id(),
            "categoryId": category_id,
            "categoryName": selected_category["categoryName"] if selected_category else "",
            "title": title,
            "author": author,
            "isbn": isbn,
            "price": price,
            "image": image,
            "readNow": 0
        }

        books_col.insert_one(new_book)

        return redirect(url_for("home"))

    return render_template("add_book.html", categories=categories)


# ------------------------------------------
# ERRORS
# ------------------------------------------
@app.errorhandler(Exception)
def handle_error(e):
    return render_template("error.html", error=e), 500


# ------------------------------------------
# RUN APP
# ------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
