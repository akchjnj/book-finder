from nt import error
from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__ )

# 環境変数読み込み
load_dotenv()
GOOGLE_BOOK_API_KEY = os.getenv("GOOGLE_BOOK_API_KEY")
GOOGLE_BOOK_API_URL = "https://www.googleapis.com/books/v1/volumes"

app = Flask(__name__)

def search_books(query, search_type = 'title', max_results=10):
    """
    Google Books APIで書籍を検索する関数
    
    Args:
        query: 検索キーワード
        search_type: 検索タイプ ('title' or 'isbn')
        max_results: 取得する最大結果数
        
    Returns:
        tuple: (books_list, total_items, error_message)
    """

    # 検索クエリ
    q = f'isbn:{query}' if search_type == 'isbn' else query
    params = {
            'q' : q,
            'key' : GOOGLE_BOOK_API_KEY,
            'maxResults' : 10
            }

    try:
        logger.info(f'API検索開始: {q}')
        response = requests.get(GOOGLE_BOOK_API_URL,params=params)
        response.raise_for_status()
        data = response.json()
        
        books = []
        total_items = data.get('totalItems',0)

        if total_items > 0:
            for item in data.get('items',[]):
                volume_info = item.get('volumeInfo',{})

                # ISBN取得
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

        logger.info(f'検索完了: {len(books)}件取得')
        # 戻り値はエラー時含めて同じ構成
        return books, total_items, None

    except requests.exceptions.Timeout:
        logger.error("APIリクエストがタイムアウトしました")
        return [], 0, "検索がタイムアウトしました。もう一度お試しください。"
    except requests.exceptions.RequestException as e:
        logger.error(f"APIリクエストエラー: {str(e)}")
        return [], 0, f"検索中にエラーが発生しました: {str(e)}"
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        return [], 0, "予期しないエラーが発生しました。"


@app.route("/")
def home():
    return render_template("index.html", title="Home")

@app.route("/search",methods=["GET","POST"])
def search():
    # もしPOSTなら＝検索クエリがある
    if request.method == 'POST':
        search_query = request.form.get('book_title').strip()
        search_type = request.form.get('search_type','title')

        if not search_query:
            return render_template('search.html',
                                    title = '書籍検索',
                                    error = '検索キーワードを入力してください。')

        books, total_items, error = search_books(search_query,search_type)

        return render_template("result.html", 
                                title="検索結果",
                                books = books,
                                total_items = total_items,
                                search_query=search_query,
                                error = error)
    # POSTではなくGET＝最初に開いたとき
    return render_template("search.html", title="書籍検索")

@app.route("/about")
def about():
    return render_template("about.html", title="このアプリについて")

if __name__ == "__main__":
    app.run(debug=True)