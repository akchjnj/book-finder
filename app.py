from nt import error
from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数読み込み
load_dotenv()
GOOGLE_BOOK_API_KEY = os.getenv("GOOGLE_BOOK_API_KEY")
CALIL_API_KEY = os.getenv("CALIL_API_KEY")
GOOGLE_BOOK_API_URL = "https://www.googleapis.com/books/v1/volumes"
CALIL_API_URL = "https://api.calil.jp"

app = Flask(__name__)


def process_book_data(item, description_limit=None):
    """
    書籍データを処理する共通関数
    
    Args:
        item: Google Books APIのitemデータ
        description_limit: 説明文の文字数制限（Noneの場合は制限なし）
    
    Returns:
        dict: 処理済みの書籍データ
    """
    volume_info = item.get("volumeInfo", {})
    
    # ISBN取得
    isbn_13 = None
    isbn_10 = None
    for identifier in volume_info.get("industryIdentifiers", []):
        if identifier["type"] == "ISBN_13":
            isbn_13 = identifier["identifier"]
        elif identifier["type"] == "ISBN_10":
            isbn_10 = identifier["identifier"]
    
    # 説明文の処理
    description = volume_info.get("description", "")
    if description_limit and description:
        description = description[:description_limit] + "..."
    
    return {
        "id": item.get("id", ""),
        "title": volume_info.get("title", ""),
        "authors": volume_info.get("authors", []),
        "publisher": volume_info.get("publisher", ""),
        "published_date": volume_info.get("publishedDate", ""),
        "language": volume_info.get("language", ""),
        "page_count": volume_info.get("pageCount", ""),
        "categories": volume_info.get("categories", []),
        "description": description,
        "thumbnail": volume_info.get("imageLinks", {}).get("thumbnail", ""),
        "preview_link": volume_info.get("previewLink", ""),
        "isbn_13": isbn_13,
        "isbn_10": isbn_10,
    }


def search_google_books(query, search_type="title", max_results=10):
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
    q = f"isbn:{query}" if search_type == "isbn" else query
    params = {"q": q, "key": GOOGLE_BOOK_API_KEY, "maxResults": max_results,"printType":"books"}

    try:
        logger.info(f"API検索開始: {q}")
        logger.info(f"検索タイプ: {search_type}")
        logger.info(f"最大結果数: {max_results}")
        logger.info(f"リクエストパラメータ: {params}")
        response = requests.get(GOOGLE_BOOK_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        books = []
        total_items = data.get("totalItems", 0)

        if total_items > 0:
            for item in data.get("items", []):
                book_data = process_book_data(item, description_limit=200)
                # 検索結果用の追加処理
                book_data["authors"] = ", ".join(book_data["authors"]) if book_data["authors"] else ""
                book_data["categories"] = ", ".join(book_data["categories"]) if book_data["categories"] else ""
                if not book_data["description"]:
                    book_data["description"] = "説明なし"
                logger.info(f"書籍ID: {book_data['id']}, タイトル: {book_data['title']}")
                books.append(book_data)

        logger.info(f"検索完了: {len(books)}件取得")

        # APIレスポンスをLoggerに出力
        logger.info("=== Google Books API Response ===")
        logger.info(f"Total Items: {total_items}")
        logger.info(f'Items Count: {len(data.get("items", []))}')
        logger.info("=== End of API Response ===")

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

def process_library_data(data):
    """
    カーリルAPIのレスポンスから図書館データを処理
    
    Args:
        data: カーリルAPIのレスポンス
    
    Returns:
        dict: 処理済みの図書館データ
    """
    try:
        # ISBNが一意なので、直接アクセス
        books_data = data.get('books', {})
        if books_data:
            # 最初のISBNを取得
            isbn = list(books_data.keys())[0]
            isbn_data = books_data[isbn]
            # システムIDも一意なので、最初のキーを取得
            system_id = list(isbn_data.keys())[0]
            system_data = isbn_data[system_id]
            
            return {
                'libkey': system_data.get('libkey', {}),
                'reserveurl': system_data.get('reserveurl', '')
            }
        return None
    except Exception as e:
        logger.error(f"図書館データ処理エラー: {str(e)}")
        return None


def search_library_availability(isbn_13=None, isbn_10=None):
    """
    カーリルAPIで図書館蔵書を検索（ISBNのみ）
    
    Args:
        isbn_13: ISBN-13
        isbn_10: ISBN-10
    
    Returns:
        dict: 蔵書検索結果
    """
    if not CALIL_API_KEY:
        logger.warning("カーリルAPIキーが設定されていません")
        return None
    
    # ISBNを優先して検索（ISBN-13を優先）
    isbn = isbn_13 or isbn_10
    if not isbn:
        logger.warning("ISBNが取得できませんでした")
        return None
    
    # 固定のシステムID
    systemid = "Hiroshima_Hiroshima"
    
    try:
        # 蔵書検索開始
        url = f"{CALIL_API_URL}/check"
        params = {
            'appkey': CALIL_API_KEY,
            'isbn': isbn,
            'systemid': systemid,
            'format': 'json',
            'callback': 'no'  # JSONPを無効にしてJSON形式で取得
        }
        
        logger.info(f"蔵書検索開始: {url}")
        logger.info(f"パラメータ: {params}")
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # デバッグ用：レスポンス内容を確認
        logger.info(f"レスポンスステータス: {response.status_code}")
        logger.info(f"レスポンスヘッダー: {response.headers}")
        logger.info(f"レスポンス内容: {response.text[:500]}")  # 最初の500文字
        
        data = response.json()
        
        # セッションIDがある場合は継続検索が必要
        session_id = data.get('session')
        if session_id:
            logger.info(f"蔵書検索継続中（セッションID: {session_id}）")
            
            # ポーリング（最大10回、2秒間隔）
            import time
            max_attempts = 10
            
            for attempt in range(max_attempts):
                time.sleep(2)  # 2秒待機
                
                # ポーリング用のリクエスト
                poll_params = {
                    'appkey': CALIL_API_KEY,
                    'session': session_id,
                    'format': 'json',
                    'callback': 'no'  # JSONPを無効にしてJSON形式で取得
                }
                
                poll_response = requests.get(url, params=poll_params)
                poll_response.raise_for_status()
                
                # デバッグ用：ポーリングレスポンス内容を確認
                logger.info(f"ポーリングレスポンス: {poll_response.text[:200]}")
                
                poll_data = poll_response.json()
                
                continue_flag = poll_data.get('continue', 0)
                if continue_flag == 0:
                    # 検索完了
                    logger.info(f"蔵書検索完了: {attempt + 1}回目のポーリング")
                    return process_library_data(poll_data)
                else:
                    # 継続中
                    logger.info(f"蔵書検索継続中: {attempt + 1}回目のポーリング")
            
            logger.warning("蔵書検索がタイムアウトしました")
            return None
        else:
            # セッションIDがない場合は即座に完了
            logger.info("蔵書検索完了（即座に結果取得）")
            return process_library_data(data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"蔵書検索APIエラー: {str(e)}")
        return None

@app.route("/")
def home():
    return render_template("index.html", title="Home")


@app.route("/search", methods=["GET", "POST"])
def search():
    # もしPOSTなら＝検索クエリがある
    if request.method == "POST":
        search_query = request.form.get("book_title").strip()
        search_type = request.form.get("search_type", "title")

        if not search_query:
            return render_template(
                "search.html",
                title="書籍検索",
                error="検索キーワードを入力してください。",
            )

        books, total_items, error = search_google_books(search_query, search_type)

        return render_template(
            "result.html",
            title="検索結果",
            books=books,
            total_items=total_items,
            search_query=search_query,
            error=error,
        )
    # POSTではなくGET＝最初に開いたとき
    return render_template("search.html", title="書籍検索")


@app.route("/book/<book_id>")
def book_detail(book_id):
    """書籍詳細ページ（図書館蔵書情報付き）"""
    try:
        # Google Books APIから書籍の詳細情報を取得（ID直接指定）
        detail_url = f"{GOOGLE_BOOK_API_URL}/{book_id}"
        params = {"key": GOOGLE_BOOK_API_KEY}

        logger.info(f"書籍詳細取得開始: {book_id}")
        logger.info(f"リクエストURL: {detail_url}")
        logger.info(f"リクエストパラメータ: {params}")
        response = requests.get(detail_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"APIレスポンス: kind={data.get('kind', 'unknown')}")
        logger.info(f"APIレスポンス: id={data.get('id', 'unknown')}")

        # ID直接指定の場合は、dataが直接itemの内容になる
        if not data.get("id"):
            return render_template(
                "book_detail.html",
                title="書籍が見つかりません",
                error="指定された書籍が見つかりませんでした。",
            )

        # 書籍情報を取得（ID直接指定の場合はdataが直接item）
        book_data = process_book_data(data)  # 説明文制限なし

        # カーリルAPIで図書館蔵書検索（ISBNのみ）
        library_info = None
        if book_data.get('isbn_13') or book_data.get('isbn_10'):
            logger.info("図書館蔵書検索を開始します")
            library_info = search_library_availability(
                isbn_13=book_data.get('isbn_13'),
                isbn_10=book_data.get('isbn_10')
            )
            if library_info:
                logger.info("図書館蔵書検索が完了しました")
            else:
                logger.warning("図書館蔵書検索に失敗しました")

        logger.info(f'書籍詳細取得完了: {book_data["title"]}')
        return render_template(
            "book_detail.html", 
            title=f"{book_data['title']} - 詳細", 
            book=book_data,
            library_info=library_info
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"書籍詳細取得エラー: {str(e)}")
        return render_template(
            "book_detail.html",
            title="エラー",
            error=f"書籍情報の取得中にエラーが発生しました: {str(e)}",
        )
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        return render_template(
            "book_detail.html", title="エラー", error="予期しないエラーが発生しました。"
        )


@app.route("/about")
def about():
    return render_template("about.html", title="このアプリについて")


if __name__ == "__main__":
    app.run(debug=True)
