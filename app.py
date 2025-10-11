from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv

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
        search_query = request.form.get('book_title')
        search_type = request.form.get('search_type','title')

        if search_query == 'isbn':
            q = f'isbn:{search_query}'
        else:
            q = search_query

        # Books API リクエスト
        params = {
            'q' : q,
            'key' : GOOGLE_BOOK_API_KEY,
            'maxResults' : 10
        }
        try:
            response = requests.get(GOOGLE_BOOK_API_URL,params=params)
            response.raise_for_status()
            data = response.json()
            print(f"Response data: {data}")  # デバッグ用
            
            books = []

            # データがあるか確認
            if data.get('totalItems',0) > 0:
                for item in data.get('items',[]):
                    volume_info = item.get('volumeInfo',{})
                    isbn_13 = None
                    isbn_10 = None
                    for identifiers in volume_info.get('industryIdentifiers',{}):
                        if identifiers['type'] == 'ISBN_13':
                            isbn_13 = identifiers['identifier']
                        elif identifiers['type'] == 'ISBN_10':
                            isbn_10 = identifiers['identifier']
                    

                    book_data = {
                        'title': volume_info.get('title','不明'),
                        'authors': ', '.join(volume_info.get('authors','不明')),
                        'publisher': volume_info.get('publisher','不明'),
                        'published_date': volume_info.get('publishedDate','不明'),
                        'thumbnail': volume_info.get('imageLinks',{}).get('thumbnail',''),
                        'isbn_13': isbn_13,
                        'isbn_10': isbn_10,
                        'description': volume_info.get('description','')[:200] + '...' if volume_info.get('description') else '説明なし'
                    }
                    books.append(book_data)
                return render_template("result.html", 
                                        title="Result",
                                        books = books,
                                        total_items = data.get('totalItems',0),
                                        search_query=search_query)
        except requests.exceptions.RequestException as e:
            return render_template('result.html',
                                    title = "Error",
                                    error = f'APIエラー：{str(e)}',
                                    search_query = search_query)
    return render_template("search.html", title="Search")

@app.route("/about")
def about():
    return render_template("about.html", title="About")

if __name__ == "__main__":
    app.run(debug=True)