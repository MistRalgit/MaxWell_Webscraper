from django.shortcuts import render, redirect, get_object_or_404
import json
import os
import time
import logging
import pandas as pd
import csv
from django.http import JsonResponse, HttpResponse, FileResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import ScrapedData
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import urllib.request
import re
import urllib.parse
import uuid
from pathlib import Path
from collections import deque
from datetime import datetime

# ロガーの設定
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(settings.BASE_DIR, 'scraper.log')),
        logging.StreamHandler()
    ]
)

# ログファイルのパスを設定
LOG_FILE = os.path.join(settings.BASE_DIR, 'scraper.log')

def index(request):
    """メインページを表示"""
    saved_data = ScrapedData.objects.all().order_by('-created_at')
    return render(request, 'scraper/index.html', {'saved_data': saved_data})

def get_webdriver():
    """Seleniumのウェブドライバーを設定して返す"""
    chrome_options = Options()
    
    # ヘッドレスモード（GUIなし）で実行（必要に応じてコメントアウト）
    # chrome_options.add_argument('--headless')
    
    # ウェブサイトに対してブラウザを偽装
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # その他の設定
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # ChromeDriverManagerを使って最新のドライバーを取得
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # JavaScriptを実行してSeleniumの検出を回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

@csrf_exempt
def run_scraper(request):
    """スクレイピングを実行"""
    if request.method == 'POST':
        try:
            # POSTデータを取得
            data = json.loads(request.body.decode('utf-8'))
            
            # 必須パラメータの確認
            urls = data.get('urls', [])
            if not urls:
                return JsonResponse({'status': 'error', 'message': 'URLが設定されていません'})
                
            extraction_selectors = data.get('extraction_selectors', {})
            if not extraction_selectors:
                return JsonResponse({'status': 'error', 'message': '抽出セレクタが設定されていません'})
            
            # オプションパラメータ
            require_login = data.get('require_login', False)
            username_selector = data.get('username_selector', '')
            password_selector = data.get('password_selector', '')
            login_button_selector = data.get('login_button_selector', '')
            username = data.get('username', '')
            password = data.get('password', '')
            
            use_pagination = data.get('use_pagination', False)
            next_button_selector = data.get('next_button_selector', '')
            max_pages = data.get('max_pages', 1)
            
            download_images = data.get('download_images', False)
            image_selector = data.get('image_selector', '')
            
            download_videos = data.get('download_videos', False)
            video_selector = data.get('video_selector', '')
            
            output_path = data.get('output_path', 'output')
            additional_url = data.get('additional_url', '')
            use_text_mode = data.get('use_text_mode', False)
            
            # 出力ディレクトリの作成
            os.makedirs(output_path, exist_ok=True)
            
            # 画像ダウンロード用ディレクトリの作成
            if download_images:
                images_dir = os.path.join(settings.IMAGES_DIR)
                os.makedirs(images_dir, exist_ok=True)
            
            # WebDriverの取得
            driver = get_webdriver()
            
            # スクレイピング開始
            logger.info("スクレイピングを開始します。")
            
            # ログイン処理（必要な場合）
            if require_login and username_selector and password_selector and login_button_selector:
                login_url = urls[0]  # 最初のURLでログイン
                logger.info(f"ログイン処理を開始します: {login_url}")
                
                driver.get(login_url)
                time.sleep(3)  # ページの読み込みを待機
                
                try:
                    # ユーザー名入力
                    user_elem = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
                    )
                    user_elem.clear()
                    user_elem.send_keys(username)
                    
                    # パスワード入力
                    pass_elem = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, password_selector))
                    )
                    pass_elem.clear()
                    pass_elem.send_keys(password)
                    
                    # ログインボタンクリック
                    login_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, login_button_selector))
                    )
                    login_button.click()
                    
                    # ログイン後の待機
                    logger.info("ログインボタンをクリックしました。ログイン処理を待機しています...")
                    time.sleep(5)
                    
                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"ログイン処理中にエラーが発生しました: {str(e)}")
                    driver.quit()
                    return JsonResponse({'status': 'error', 'message': f'ログイン処理中にエラーが発生しました: {str(e)}'})
            
            # データ収集
            all_data = []
            column_names = list(extraction_selectors.keys())
            
            # 各URLについてスクレイピング
            for url in urls:
                if not url:
                    continue
                    
                logger.info(f"URLにアクセスしています: {url}")
                driver.get(url)
                time.sleep(3)  # ページの読み込みを待機
                
                # 追加URLがある場合は処理
                if additional_url:
                    combined_url = url + additional_url
                    logger.info(f"追加URLにアクセスしています: {combined_url}")
                    driver.get(combined_url)
                    time.sleep(3)
                
                page_counter = 1
                
                while True:
                    logger.info(f"ページ {page_counter} のスクレイピングを開始します")
                    
                    # 各セレクタに対して要素を取得
                    page_data = []
                    
                    # 各選択子について処理
                    for column, selector in extraction_selectors.items():
                        try:
                            # 要素が表示されるまで待機
                            elements = WebDriverWait(driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                            )
                            
                            # 各要素から値を取得
                            values = []
                            for element in elements:
                                if use_text_mode:
                                    values.append(element.text.strip())
                                else:
                                    values.append(element.get_attribute('innerText').strip())
                                    
                                # 画像ダウンロードが有効で、画像セレクタが指定されている場合
                                if download_images and image_selector:
                                    try:
                                        # 現在の要素内から画像を探す
                                        img_elements = element.find_elements(By.CSS_SELECTOR, image_selector)
                                        
                                        for i, img in enumerate(img_elements):
                                            src = img.get_attribute('src')
                                            if src:
                                                # 画像URLが動画ファイルを参照しているかチェック
                                                video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.wmv', '.flv', '.mkv']
                                                is_video_file = any(src.lower().endswith(ext) for ext in video_extensions)
                                                
                                                # data-video属性や動画リンクをチェック
                                                video_url = img.get_attribute('data-video') or img.get_attribute('data-video-src')
                                                parent_a = None
                                                try:
                                                    # 親要素がaタグで、動画へのリンクかチェック
                                                    parent_a = img.find_element(By.XPATH, "./..")
                                                    if parent_a.tag_name.lower() == 'a':
                                                        href = parent_a.get_attribute('href')
                                                        if href and any(href.lower().endswith(ext) for ext in video_extensions):
                                                            video_url = href
                                                except:
                                                    pass
                                                
                                                # 動画ファイルの場合は動画としてダウンロード
                                                if is_video_file or video_url:
                                                    # 動画ディレクトリが作成されていない場合は作成
                                                    if not 'videos_dir' in locals():
                                                        videos_dir = os.path.join(settings.VIDEOS_DIR)
                                                        os.makedirs(videos_dir, exist_ok=True)
                                                    
                                                    video_target_url = video_url if video_url else src
                                                    video_filename = f"{len(all_data) + len(page_data)}_{i}_{os.path.basename(video_target_url)}"
                                                    video_path = os.path.join(videos_dir, video_filename)
                                                    
                                                    try:
                                                        urllib.request.urlretrieve(video_target_url, video_path)
                                                        logger.info(f"画像要素から動画をダウンロードしました: {video_path}")
                                                        # 結果に動画パスを含める
                                                        if not any(header == '動画パス' for header in column_names):
                                                            column_names.append('動画パス')
                                                        # この要素の最後に動画パスを追加（後で行に追加する際に使用）
                                                        values.append(video_path)
                                                    except Exception as e:
                                                        logger.error(f"動画ダウンロード中にエラーが発生: {str(e)}")
                                                else:
                                                    # 通常の画像ファイルとしてダウンロード
                                                    img_filename = f"{len(all_data) + len(page_data)}_{i}_{os.path.basename(src)}"
                                                    img_path = os.path.join(images_dir, img_filename)
                                                    urllib.request.urlretrieve(src, img_path)
                                                    values.append(img_path)
                                    except Exception as e:
                                        logger.error(f"画像要素の検索中にエラーが発生しました: {str(e)}")
                            
                            # 要素ごとにデータ行を作成
                            for i, value in enumerate(values):
                                if i >= len(page_data):
                                    page_data.append({})
                                page_data[i][column] = value
                                
                        except (TimeoutException, NoSuchElementException) as e:
                            logger.warning(f"セレクタ '{selector}' の要素が見つかりませんでした: {str(e)}")
                    
                    # 収集したデータを追加
                    all_data.extend(page_data)
                    logger.info(f"ページ {page_counter} から {len(page_data)} 件のデータを取得しました")
                    
                    # ページネーションが有効で、次へボタンが存在し、最大ページ数に達していない場合
                    if (use_pagination and next_button_selector and 
                        page_counter < max_pages):
                        try:
                            next_button = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector))
                            )
                            next_button.click()
                            logger.info("次のページに移動しています...")
                            time.sleep(3)  # ページ遷移を待機
                            page_counter += 1
                        except (TimeoutException, NoSuchElementException) as e:
                            logger.info(f"次へボタンが見つからないか、クリックできないため終了します: {str(e)}")
                            break
                    else:
                        break
            
            # WebDriverを閉じる
            driver.quit()
            
            # データをCSVに保存
            csv_path = os.path.join(output_path, 'scraped_data.csv')
            
            # Pandasを使用してデータフレームに変換
            df = pd.DataFrame(all_data)
            
            # CSVとして保存（日本語文字化けを防ぐためにUTF-8で保存）
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            logger.info(f"スクレイピングが完了しました。{len(all_data)} 件のデータを取得しました。")
            logger.info(f"データを保存しました: {csv_path}")
            
            return JsonResponse({
                'status': 'success', 
                'message': f'スクレイピングが完了しました。{len(all_data)} 件のデータを取得しました。',
                'data_count': len(all_data),
                'csv_path': csv_path
            })
            
        except Exception as e:
            logger.error(f"スクレイピング中にエラーが発生しました: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'エラーが発生しました: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': '不正なリクエストです'})

@csrf_exempt
def test_selector(request):
    """セレクタのテストを実行"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            url = data.get('url', '')
            selector = data.get('selector', '')
            
            if not url or not selector:
                return JsonResponse({'status': 'error', 'message': 'URLとセレクタの両方を指定してください'})
            
            # WebDriverの取得
            driver = get_webdriver()
            
            # URLにアクセス
            logger.info(f"セレクタテスト: URLにアクセスしています: {url}")
            driver.get(url)
            time.sleep(3)  # ページの読み込みを待機
            
            try:
                # 要素が表示されるまで待機
                elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                
                # 要素のテキストを取得
                result = []
                for i, element in enumerate(elements[:10]):  # 最初の10件のみ取得
                    result.append({
                        'index': i,
                        'text': element.text.strip() or element.get_attribute('innerText').strip(),
                        'html': element.get_attribute('outerHTML')
                    })
                
                # WebDriverを閉じる
                driver.quit()
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'{len(elements)} 件の要素が見つかりました。',
                    'results': result,
                    'total_count': len(elements)
                })
                
            except (TimeoutException, NoSuchElementException) as e:
                driver.quit()
                logger.warning(f"セレクタテスト: 要素が見つかりませんでした: {str(e)}")
                return JsonResponse({'status': 'error', 'message': f'指定されたセレクタに一致する要素が見つかりませんでした: {str(e)}'})
                
        except Exception as e:
            logger.error(f"セレクタテスト中にエラーが発生しました: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'エラーが発生しました: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': '不正なリクエストです'})

def scrape(request):
    """データスクレイピングを実行"""
    if request.method == 'POST':
        url = request.POST.get('url')
        selector = request.POST.get('selector')
        login_required = request.POST.get('login_required') == 'yes'
        pagination = request.POST.get('pagination') == 'yes'
        download_images = request.POST.get('download_images') == 'yes'
        download_videos = request.POST.get('download_videos') == 'yes'
        follow_links = request.POST.get('follow_links') == 'yes'  # リンク先を自動的に参照するかどうか
        link_depth = int(request.POST.get('link_depth', '1'))  # リンクを辿る深さ（デフォルトは1）
        
        # 結果を格納するリスト
        results = []
        headers = ['テキスト', 'リンク']
        
        try:
            # Chromeドライバーの設定
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # ChromeDriverManagerを使用して自動的にドライバーをインストール
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # URLにアクセス
            driver.get(url)
            
            # ログインが必要な場合
            if login_required:
                username = request.POST.get('username')
                password = request.POST.get('password')
                username_selector = request.POST.get('username_selector')
                password_selector = request.POST.get('password_selector')
                login_button_selector = request.POST.get('login_button_selector')
                
                try:
                    # ユーザー名入力
                    username_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
                    )
                    username_field.send_keys(username)
                    
                    # パスワード入力
                    password_field = driver.find_element(By.CSS_SELECTOR, password_selector)
                    password_field.send_keys(password)
                    
                    # ログインボタンクリック
                    login_button = driver.find_element(By.CSS_SELECTOR, login_button_selector)
                    login_button.click()
                    
                    # ログイン後のページ読み込みを待機
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"ログイン処理中にエラーが発生: {str(e)}")
                    messages.error(request, f"ログイン処理中にエラーが発生しました: {str(e)}")
                    driver.quit()
                    return render(request, 'scraper/index.html', {'error': str(e)})
            
            # 変数を初期化
            image_selector = ""
            video_selector = ""
            
            # 画像ディレクトリの作成
            if download_images:
                image_selector = request.POST.get('image_selector')
                os.makedirs(settings.IMAGES_DIR, exist_ok=True)
                
            # 動画ディレクトリの作成
            if download_videos:
                video_selector = request.POST.get('video_selector')
                videos_dir = os.path.join(settings.VIDEOS_DIR)
                os.makedirs(videos_dir, exist_ok=True)
            
            # 処理済みのURLを追跡するセット
            processed_urls = set()
            processed_urls.add(url)
            
            # リンク先のURLを追跡する辞書 (URL -> 深さ)
            links_to_process = {}
            
            # メインURLのスクレイピング
            scrape_page(driver, url, selector, download_images, image_selector, download_videos, video_selector, 
                      pagination, request.POST.get('next_page_selector'), int(request.POST.get('max_pages', 1)), 
                      results, headers, processed_urls, links_to_process, follow_links, 0, link_depth)
            
            # リンク先URLのスクレイピング
            if follow_links and links_to_process:
                for link_url, depth in list(links_to_process.items()):
                    if link_url not in processed_urls and depth < link_depth:
                        logger.info(f"リンク先URLにアクセスしています（深さ {depth+1}）: {link_url}")
                        try:
                            # 同じセレクタを使用してリンク先のページをスクレイピング
                            scrape_page(driver, link_url, selector, download_images, image_selector, download_videos, video_selector, 
                                      False, None, 1, results, headers, processed_urls, links_to_process, follow_links, depth+1, link_depth)
                        except Exception as e:
                            logger.error(f"リンク先のスクレイピング中にエラーが発生: {str(e)}")
            
            driver.quit()
            
            # 結果をセッションに保存
            request.session['scraping_results'] = results
            request.session['scraping_headers'] = headers
            
            # 結果をCSVに保存
            df = pd.DataFrame(results, columns=headers)
            csv_path = os.path.join(settings.BASE_DIR, 'results.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            messages.success(request, f"スクレイピングが完了しました。{len(results)}件のデータを取得しました。")
            
            # 保存済みデータを取得
            saved_data = ScrapedData.objects.all().order_by('-created_at')
            
            return render(request, 'scraper/index.html', {
                'results': results,
                'headers': headers,
                'saved_data': saved_data
            })
            
        except Exception as e:
            logger.error(f"スクレイピング実行中にエラーが発生: {str(e)}")
            messages.error(request, f"エラーが発生しました: {str(e)}")
            return render(request, 'scraper/index.html', {'error': str(e)})
    
    return redirect('scraper:index')

def clean_url(url):
    """
    URLを安全で有効な形式に整形する
    """
    if not url:
        return ""
    
    # URLをデコード
    url = urllib.parse.unquote(url)
    
    # スキームがない場合は追加（例: //example.com/image.jpg → https://example.com/image.jpg）
    if url.startswith('//'):
        url = 'https:' + url
    
    # 相対パスの場合はスキップ（後で処理）
    if not url.startswith(('http://', 'https://', 'ftp://')):
        return url
    
    # URLを正規化
    try:
        parsed = urllib.parse.urlparse(url)
        return urllib.parse.urlunparse(parsed)
    except Exception:
        return url

def safe_filename_from_url(url, prefix="", max_length=100):
    """
    URLから安全なファイル名を生成
    
    Args:
        url: 元のURL
        prefix: ファイル名の接頭辞
        max_length: ファイル名の最大長（拡張子を除く）
    
    Returns:
        安全なファイル名
    """
    if not url:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    # URLからクエリパラメータとフラグメントを削除
    url_without_query = url.split('?')[0].split('#')[0]
    
    # パスの最後の部分を取得
    filename = os.path.basename(url_without_query)
    
    # ファイル名と拡張子を分離
    name, ext = os.path.splitext(filename)
    
    # ファイル名に使用できない文字を置換
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    
    # ファイル名が空の場合、uuidで置き換え
    if not name:
        name = uuid.uuid4().hex[:8]
    
    # ファイル名が長すぎる場合は切り詰め
    if len(name) > max_length:
        name = name[:max_length]
    
    # プレフィックスを追加して一意なファイル名を生成
    unique_name = f"{prefix}_{name}_{uuid.uuid4().hex[:6]}{ext}"
    
    return unique_name

def ensure_dir(directory):
    """ディレクトリが存在することを確認し、存在しない場合は作成"""
    os.makedirs(directory, exist_ok=True)
    return directory

def download_file(url, save_path, timeout=30):
    """
    URLからファイルをダウンロードする関数
    
    Args:
        url: ダウンロードするファイルのURL
        save_path: 保存先のパス
        timeout: タイムアウト秒数
    
    Returns:
        成功時はTrue、失敗時はFalse
    """
    try:
        # URLをクリーニング
        cleaned_url = clean_url(url)
        if not cleaned_url:
            return False
        
        # ディレクトリが存在することを確認
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # ファイルをダウンロード
        urllib.request.urlretrieve(cleaned_url, save_path)
        
        # ファイルが実際に作成されたか確認
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            return True
        else:
            if os.path.exists(save_path):
                os.remove(save_path)  # 空のファイルを削除
            return False
            
    except Exception as e:
        logger.error(f"ファイルダウンロード中にエラーが発生: {str(e)}, URL: {url}")
        if os.path.exists(save_path):
            try:
                os.remove(save_path)  # 不完全なファイルを削除
            except:
                pass
        return False

def scrape_page(driver, url, selector, download_images, image_selector, download_videos, video_selector, 
               pagination, next_page_selector, max_pages, results, headers, processed_urls, links_to_process, 
               follow_links, current_depth, max_depth):
    """ページのスクレイピングを実行する補助関数"""
    try:
        # URLにアクセス（すでに開いているURLと同じ場合はスキップ）
        if driver.current_url != url:
            driver.get(url)
            time.sleep(3)  # ページの読み込みを待機
        
        # 処理済みURLとして記録
        processed_urls.add(url)
        
        page_count = 1
        while page_count <= max_pages:
            # 要素の取得を待機
            try:
                elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                
                for element in elements:
                    # テキストとリンクを取得
                    text = element.text.strip()
                    
                    # リンクを取得
                    link = ""
                    try:
                        link_element = element.find_element(By.TAG_NAME, 'a')
                        link = link_element.get_attribute('href')
                        
                        # リンク先を処理対象としてリストに追加（フォローが有効な場合）
                        if follow_links and link and link not in processed_urls and current_depth < max_depth:
                            links_to_process[link] = current_depth
                    except:
                        pass
                    
                    # 画像をダウンロード
                    image_path = ""
                    if download_images and image_selector:
                        try:
                            img_elements = element.find_elements(By.CSS_SELECTOR, image_selector)
                            for i, img in enumerate(img_elements):
                                img_url = img.get_attribute('src')
                                if not img_url:
                                    # srcがない場合はdata-srcなど他の属性を確認
                                    for attr in ['data-src', 'data-lazy-src', 'data-original']:
                                        img_url = img.get_attribute(attr)
                                        if img_url:
                                            break

                                if img_url:
                                    # 相対URLを絶対URLに変換
                                    if img_url.startswith('/'):
                                        # URLからベースURLを取得
                                        parsed_url = urllib.parse.urlparse(url)
                                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                        img_url = urllib.parse.urljoin(base_url, img_url)
                                    elif not img_url.startswith(('http://', 'https://', 'ftp://', '//')):
                                        img_url = urllib.parse.urljoin(url, img_url)

                                    # 画像URLが動画ファイルを参照しているかチェック
                                    video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.wmv', '.flv', '.mkv']
                                    is_video_file = any(img_url.lower().endswith(ext) for ext in video_extensions)
                                    
                                    # data-video属性や動画リンクをチェック
                                    video_url = img.get_attribute('data-video') or img.get_attribute('data-video-src')
                                    parent_a = None
                                    try:
                                        # 親要素がaタグで、動画へのリンクかチェック
                                        parent_a = img.find_element(By.XPATH, "./..")
                                        if parent_a.tag_name.lower() == 'a':
                                            href = parent_a.get_attribute('href')
                                            if href and any(href.lower().endswith(ext) for ext in video_extensions):
                                                video_url = href
                                    except:
                                        pass
                                    
                                    # 動画ファイルの場合は動画としてダウンロード
                                    if is_video_file or video_url:
                                        # 動画ディレクトリの確保
                                        videos_dir = ensure_dir(settings.VIDEOS_DIR)
                                        
                                        video_target_url = video_url if video_url else img_url
                                        video_filename = safe_filename_from_url(video_target_url, f"video_{len(results)}_{i}")
                                        video_path = os.path.join(videos_dir, video_filename)
                                        
                                        # 動画をダウンロード
                                        if download_file(video_target_url, video_path):
                                            logger.info(f"画像要素から動画をダウンロードしました: {video_path}")
                                            # 結果に動画パスを含める
                                            if not any(header == '動画パス' for header in headers):
                                                headers.append('動画パス')
                                            # この要素の最後に動画パスを追加（後で行に追加する際に使用）
                                            image_path = video_path
                                    else:
                                        # 通常の画像ファイルとしてダウンロード
                                        images_dir = ensure_dir(settings.IMAGES_DIR)
                                        img_filename = safe_filename_from_url(img_url, f"img_{len(results)}_{i}")
                                        img_path = os.path.join(images_dir, img_filename)
                                        
                                        # 画像をダウンロード
                                        if download_file(img_url, img_path):
                                            image_path = img_path
                        except Exception as e:
                            logger.error(f"画像ダウンロード中にエラーが発生: {str(e)}")
                    
                    # 動画をダウンロード
                    video_path = ""
                    if download_videos and video_selector:
                        try:
                            video_elements = element.find_elements(By.CSS_SELECTOR, video_selector)
                            for i, video in enumerate(video_elements):
                                # video要素の場合
                                video_url = video.get_attribute('src')
                                
                                # src属性がない場合はsource要素を確認
                                if not video_url:
                                    source_elements = video.find_elements(By.TAG_NAME, 'source')
                                    if source_elements:
                                        video_url = source_elements[0].get_attribute('src')
                                
                                # iframe内の動画の場合
                                if not video_url and video.tag_name.lower() == 'iframe':
                                    video_url = video.get_attribute('src')
                                
                                # data-src属性も確認
                                if not video_url:
                                    for attr in ['data-src', 'data-lazy-src']:
                                        temp_url = video.get_attribute(attr)
                                        if temp_url:
                                            video_url = temp_url
                                            break
                                
                                if video_url:
                                    # 相対URLを絶対URLに変換
                                    if video_url.startswith('/'):
                                        # URLからベースURLを取得
                                        parsed_url = urllib.parse.urlparse(url)
                                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                        video_url = urllib.parse.urljoin(base_url, video_url)
                                    elif not video_url.startswith(('http://', 'https://', 'ftp://', '//')):
                                        video_url = urllib.parse.urljoin(url, video_url)
                                    
                                    # 動画ディレクトリの確保
                                    videos_dir = ensure_dir(settings.VIDEOS_DIR)
                                    video_filename = safe_filename_from_url(video_url, f"video_{len(results)}_{i}")
                                    video_path = os.path.join(videos_dir, video_filename)
                                    
                                    # 動画をダウンロード
                                    if download_file(video_url, video_path):
                                        logger.info(f"動画をダウンロードしました: {video_path}")
                                        if not any(header == '動画パス' for header in headers):
                                            headers.append('動画パス')
                        except Exception as e:
                            logger.error(f"動画ダウンロード中にエラーが発生: {str(e)}")
                    
                    # リンク元ページの情報を追加（深さが0より大きい場合）
                    source_info = ""
                    if current_depth > 0:
                        if not any(header == 'リンク元' for header in headers):
                            headers.append('リンク元')
                        source_info = url
                    
                    # リンクの深さを記録
                    depth_info = ""
                    if follow_links:
                        if not any(header == '深さ' for header in headers):
                            headers.append('深さ')
                        depth_info = str(current_depth)
                    
                    # 結果に追加
                    row = [text, link]
                    if download_images:
                        row.append(image_path)
                        if len(results) == 0:
                            if not any(header == '画像パス' for header in headers):
                                headers.append('画像パス')
                    
                    if download_videos:
                        row.append(video_path)
                        if len(results) == 0:
                            if not any(header == '動画パス' for header in headers):
                                headers.append('動画パス')
                    
                    if current_depth > 0:
                        row.append(source_info)
                    
                    if follow_links:
                        row.append(depth_info)
                    
                    results.append(row)
                
                # 次のページへ移動（ページネーションが有効な場合）
                if pagination and page_count < max_pages and next_page_selector:
                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, next_page_selector)
                        next_button.click()
                        time.sleep(2)  # ページ読み込みを待機
                        page_count += 1
                    except NoSuchElementException:
                        logger.info("次のページが見つかりません。ページネーション終了。")
                        break
                else:
                    break
                
            except TimeoutException:
                logger.error(f"要素の取得がタイムアウトしました: {selector}")
                break
            except Exception as e:
                logger.error(f"ページのスクレイピング中にエラーが発生: {str(e)}")
                break
    except Exception as e:
        logger.error(f"ページの処理中にエラーが発生: {str(e)}")
        raise

def export_csv(request):
    """スクレイピング結果をCSVファイルとしてエクスポート"""
    if request.method == 'POST':
        results = request.session.get('scraping_results', [])
        headers = request.session.get('scraping_headers', [])
        
        if results:
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = 'attachment; filename="scraping_results.csv"'
            
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(results)
            
            return response
    
    messages.error(request, "エクスポートするデータがありません。")
    return redirect('scraper:index')

def save_data(request):
    """スクレイピング結果をデータベースに保存"""
    if request.method == 'POST':
        save_name = request.POST.get('save_name')
        results = request.session.get('scraping_results', [])
        headers = request.session.get('scraping_headers', [])
        
        if results and save_name:
            # JSONに変換して保存
            data_json = json.dumps({
                'results': results,
                'headers': headers
            })
            
            # データベースに保存
            scraped_data = ScrapedData(
                name=save_name,
                data=data_json
            )
            scraped_data.save()
            
            messages.success(request, f"データを '{save_name}' として保存しました。")
        else:
            messages.error(request, "保存するデータがないか、名前が指定されていません。")
    
    return redirect('scraper:index')

def load_data(request, data_id):
    """保存されたデータを読み込む"""
    scraped_data = get_object_or_404(ScrapedData, id=data_id)
    
    try:
        data = json.loads(scraped_data.data)
        results = data.get('results', [])
        headers = data.get('headers', [])
        
        # セッションに保存
        request.session['scraping_results'] = results
        request.session['scraping_headers'] = headers
        
        messages.success(request, f"'{scraped_data.name}' のデータを読み込みました。")
        
        # 保存済みデータを取得
        saved_data = ScrapedData.objects.all().order_by('-created_at')
        
        return render(request, 'scraper/index.html', {
            'results': results,
            'headers': headers,
            'saved_data': saved_data
        })
        
    except Exception as e:
        logger.error(f"データ読み込み中にエラーが発生: {str(e)}")
        messages.error(request, f"データの読み込み中にエラーが発生しました: {str(e)}")
    
    return redirect('scraper:index')

def delete_data(request, data_id):
    """保存済みデータの削除"""
    try:
        data = ScrapedData.objects.get(pk=data_id)
        data.delete()
        messages.success(request, '保存データを削除しました。')
    except ScrapedData.DoesNotExist:
        messages.error(request, '指定されたデータが見つかりませんでした。')
    
    return redirect('scraper:index')

def get_logs(request):
    """ログファイルの内容を取得して返す"""
    try:
        # パラメータを取得
        lines_limit = request.GET.get('lines', '100')
        log_level = request.GET.get('level', 'all')
        search_term = request.GET.get('search', '')
        
        try:
            lines_limit = int(lines_limit)
            if lines_limit <= 0:
                lines_limit = 100
        except ValueError:
            lines_limit = 100
        
        # ログファイルが存在するか確認
        if not os.path.exists(LOG_FILE):
            return JsonResponse({
                'status': 'error',
                'message': 'ログファイルが見つかりません',
                'logs': []
            })
        
        # ファイルサイズを確認
        file_size = os.path.getsize(LOG_FILE)
        if file_size == 0:
            return JsonResponse({
                'status': 'success',
                'logs': [],
                'last_modified': datetime.datetime.fromtimestamp(
                    os.path.getmtime(LOG_FILE)
                ).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # ログレベルごとの正規表現パターン
        level_patterns = {
            'debug': r'^\[.*?\]\s+DEBUG\s+',
            'info': r'^\[.*?\]\s+INFO\s+',
            'warning': r'^\[.*?\]\s+WARNING\s+',
            'error': r'^\[.*?\]\s+ERROR\s+',
        }
        
        # ログレベルに応じたフィルタパターン
        filter_pattern = None
        if log_level != 'all' and log_level in level_patterns:
            filter_pattern = re.compile(level_patterns[log_level])
        
        # 検索パターン
        search_pattern = None
        if search_term:
            try:
                search_pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            except re.error:
                # 正規表現エラーの場合は単純な文字列検索に戻す
                pass
        
        # ログを逆順で必要な行数分だけ読み込む
        logs = []
        log_lines = []
        
        # 大きなファイルを効率的に扱うための処理
        if file_size > 10 * 1024 * 1024:  # 10MB以上の場合
            # ファイルの末尾から指定行数*平均行サイズの分だけ読み込む
            avg_line_size = 200  # 平均行サイズを仮定
            read_size = min(file_size, lines_limit * avg_line_size * 2)  # 余裕を持って2倍
            
            with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(max(0, file_size - read_size))
                # 行の途中から読み始める場合は最初の不完全な行をスキップ
                if file_size > read_size:
                    f.readline()
                # 残りの行を読み込む
                log_lines = f.readlines()
        else:
            # 小さいファイルはすべて読み込む
            with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                log_lines = f.readlines()
        
        # ログを逆順に処理
        for line in reversed(log_lines):
            line = line.strip()
            if not line:
                continue
            
            # ログレベルによるフィルタリング
            if filter_pattern and not filter_pattern.search(line):
                continue
            
            # 検索語によるフィルタリング
            if search_pattern:
                if isinstance(search_pattern, re.Pattern):
                    if not search_pattern.search(line):
                        continue
                elif search_term.lower() not in line.lower():
                    continue
            
            # ログクラスを判断
            log_class = 'log-info'  # デフォルト
            if '[DEBUG]' in line or ' DEBUG ' in line:
                log_class = 'log-debug'
            elif '[INFO]' in line or ' INFO ' in line:
                log_class = 'log-info'
            elif '[WARNING]' in line or ' WARNING ' in line:
                log_class = 'log-warning'
            elif '[ERROR]' in line or ' ERROR ' in line:
                log_class = 'log-error'
            
            logs.append({
                'text': line,
                'class': log_class
            })
            
            # 指定行数に達したら終了
            if len(logs) >= lines_limit:
                break
        
        # 最終更新日時
        last_modified = datetime.datetime.fromtimestamp(
            os.path.getmtime(LOG_FILE)
        ).strftime('%Y-%m-%d %H:%M:%S')
        
        return JsonResponse({
            'status': 'success',
            'logs': logs,
            'last_modified': last_modified
        })
    
    except Exception as e:
        logger.exception(f"ログ取得中にエラーが発生: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f"ログの取得に失敗しました: {str(e)}",
            'logs': []
        })

def clear_logs(request):
    """ログファイルをクリアする"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'POSTリクエストが必要です'
        })
    
    try:
        # ログファイルが存在する場合はクリア
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as f:
                pass  # ファイルを空にする
            
            logger.info("ログファイルがクリアされました")
            return JsonResponse({
                'status': 'success',
                'message': 'ログがクリアされました'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'ログファイルが見つかりません'
            })
    
    except Exception as e:
        logger.exception(f"ログクリア中にエラーが発生: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f"ログのクリアに失敗しました: {str(e)}"
        })
