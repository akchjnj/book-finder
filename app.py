from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv
from urllib3 import response

# 環境変数読み込み
load_dotenv()
GOOGLE_BOOK_API_KEY = os.getenv("GOOGLE_BOOK_API_KEY")
GOOGLE_BOOK_API_URL = "https://www.googleapis.com/books/v1/volumes"

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", title="Home")

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == 'POST':
        book_title = request.form.get('book_title')

        # Books API リクエスト
        params = {
            'q' : book_title,
            'key' : GOOGLE_BOOK_API_KEY,
            'maxResults' : 1
        }
        try:
            response = requests.get(GOOGLE_BOOK_API_URL,params=params)
            response.raise_for_status()
            data = response.json()
            
            # データがあるか確認
            if data.get('totalItems',0) > 0:
                book = data['items'][0]['volumeInfo']
                book_data = {
                    'title': book.get('title','不明'),
                    'authors': book.get('authors','不明'),
                    'publisher': book.get('publisher','不明'),
                    'thumbnail': book.get('imageLinks',{}).get('thumbnail','')
                }
                return render_template("result.html", 
                                    title="Result",
                                    book = book_data, 
                                    search_query=book_title)
        except requests.exceptions.RequestException as e:
            return render_template('result.html',
                                    title = "Error",
                                    error = f'APIエラー：{str(e)}',
                                    search_query = book_title)
    return render_template("search.html", title="Search")

@app.route("/about")
def about():
    return render_template("about.html", title="About")

if __name__ == "__main__":
    app.run(debug=True)