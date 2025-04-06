import json
import os
import time
import logging
import pandas as pd
import csv
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import urllib.request

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

def index(request):
    """メインページを表示"""
    return render(request, 'scraper/index.html')

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
                                                img_filename = f"{len(all_data) + len(page_data)}_{i}_{src.split('/')[-1]}"
                                                img_path = os.path.join(settings.IMAGES_DIR, img_filename)
                                                
                                                try:
                                                    urllib.request.urlretrieve(src, img_path)
                                                    logger.info(f"画像をダウンロードしました: {img_filename}")
                                                except Exception as e:
                                                    logger.error(f"画像ダウンロード中にエラーが発生しました: {str(e)}")
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