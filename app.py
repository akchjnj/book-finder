from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", title="Home")

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == 'POST':
        book_title = request.form.get('book_title')
        return render_template("result.html", title="Result", book_title=book_title)
    return render_template("search.html", title="Search")

@app.route("/about")
def about():
    return render_template("about.html", title="About")

if __name__ == "__main__":
    app.run(debug=True)