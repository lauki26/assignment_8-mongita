from flask import Flask, render_template, request, redirect, url_for
from mongita import MongitaClientDisk
import json

app = Flask(__name__)

client = MongitaClientDisk("mongita_data")
db = client.bookstore
categories_col = db.category
books_col = db.book


def get_all_categories():
    return sorted(list(categories_col.find({})), key=lambda c: c["categoryId"])


def get_next_id(collection, id_field):
    docs = list(collection.find({}))
    if not docs:
        return 1
    return max(d.get(id_field, 0) for d in docs) + 1

@app.route("/")
def home():
    categories = get_all_categories()
    return render_template("index.html", categories=categories)


@app.route("/read")
def read():
    categories = get_all_categories()
    books = sorted(list(books_col.find({})), key=lambda b: b["bookId"])
    return render_template("read.html", books=books, categories=categories)


@app.route("/create")
def create():
    categories = get_all_categories()
    return render_template("create.html", categories=categories)


@app.route("/create_post", methods=["POST"])
def create_post():
    try:
        cat_id = int(request.form["categoryId"])
        cat = categories_col.find_one({"categoryId": cat_id})
        cat_name = cat["categoryName"] if cat else ""

        new_book = {
            "bookId": get_next_id(books_col, "bookId"),
            "categoryId": cat_id,
            "categoryName": cat_name,
            "title": request.form["title"].strip(),
            "author": request.form["author"].strip(),
            "isbn": request.form["isbn"].strip(),
            "price": float(request.form["price"]),
            "image": request.form["image"].strip(),
            "readNow": int(request.form.get("readNow", 0)),
        }
        books_col.insert_one(new_book)
        return redirect(url_for("read"))
    except Exception as e:
        categories = get_all_categories()
        return render_template("error.html", error=str(e), categories=categories), 500


@app.route("/edit/<int:book_id>")
def edit(book_id):
    book = books_col.find_one({"bookId": book_id})
    if not book:
        categories = get_all_categories()
        return render_template("error.html", error=f"Book {book_id} not found.", categories=categories), 404
    categories = get_all_categories()
    return render_template("edit.html", book=book, categories=categories)


@app.route("/edit_post/<int:book_id>", methods=["POST"])
def edit_post(book_id):
    try:
        cat_id = int(request.form["categoryId"])
        cat = categories_col.find_one({"categoryId": cat_id})
        cat_name = cat["categoryName"] if cat else ""

        books_col.replace_one(
            {"bookId": book_id},
            {
                "bookId": book_id,
                "categoryId": cat_id,
                "categoryName": cat_name,
                "title": request.form["title"].strip(),
                "author": request.form["author"].strip(),
                "isbn": request.form["isbn"].strip(),
                "price": float(request.form["price"]),
                "image": request.form["image"].strip(),
                "readNow": int(request.form.get("readNow", 0)),
            },
        )
        return redirect(url_for("read"))
    except Exception as e:
        categories = get_all_categories()
        return render_template("error.html", error=str(e), categories=categories), 500


@app.route("/delete/<int:book_id>")
def delete(book_id):
    books_col.delete_one({"bookId": book_id})
    return redirect(url_for("read"))




# ── Additional Routes (used by nav/templates) ────────────────────────────────

@app.route("/add_book")
def add_book():
    """Alias so the header Add Book link works -- redirects to /create."""
    return redirect(url_for("create"))


@app.route("/category/<int:categoryId>")
def category(categoryId):
    categories = get_all_categories()
    selected = categories_col.find_one({"categoryId": categoryId})
    books = sorted(
        list(books_col.find({"categoryId": categoryId})),
        key=lambda b: b["bookId"]
    )
    return render_template(
        "category.html",
        categories=categories,
        selectedCategory=selected,
        books=books,
        searchTerm=None,
        nothingFound=False
    )


@app.route("/search", methods=["POST"])
def search():
    categories = get_all_categories()
    term = request.form.get("search", "").strip()
    all_books = list(books_col.find({}))
    books = [b for b in all_books if term.lower() in b.get("title", "").lower()]
    books.sort(key=lambda b: b["bookId"])
    return render_template(
        "category.html",
        categories=categories,
        selectedCategory=None,
        books=books,
        searchTerm=term,
        nothingFound=(len(books) == 0)
    )


@app.route("/book_detail/<int:bookId>")
def book_detail(bookId):
    book = books_col.find_one({"bookId": bookId})
    if not book:
        categories = get_all_categories()
        return render_template(
            "error.html",
            error=f"Book {bookId} not found.",
            categories=categories
        ), 404
    categories = get_all_categories()
    return render_template("book_detail.html", book=book, categories=categories)

def export_json():
    def to_serializable(docs):
        result = []
        for d in docs:
            d.pop("_id", None)
            result.append(d)
        return result

    json.dump(to_serializable(list(categories_col.find({}))),
              open("categories.json", "w"), indent=2)
    json.dump(to_serializable(list(books_col.find({}))),
              open("books.json", "w"), indent=2)


if __name__ == "__main__":
    try:
        export_json()
    except Exception as e:
        print(f"[Warning] Could not write JSON exports: {e}")
    app.run(debug=True)
