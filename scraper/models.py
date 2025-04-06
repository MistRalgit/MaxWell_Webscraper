from django.db import models
import json
import os

class ScraperConfig(models.Model):
    """スクレイピングの設定を保存するモデル"""
    name = models.CharField(max_length=200, verbose_name="設定名")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    
    # 基本設定
    urls = models.TextField(verbose_name="スクレイピング対象URL（JSON形式）")
    additional_url = models.CharField(max_length=255, blank=True, null=True, verbose_name="追加URL")
    
    # ログイン設定
    require_login = models.BooleanField(default=False, verbose_name="ログインが必要")
    username_selector = models.CharField(max_length=255, blank=True, null=True, verbose_name="ユーザー名セレクタ")
    password_selector = models.CharField(max_length=255, blank=True, null=True, verbose_name="パスワードセレクタ")
    login_button_selector = models.CharField(max_length=255, blank=True, null=True, verbose_name="ログインボタンセレクタ")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="ユーザー名")
    password = models.CharField(max_length=255, blank=True, null=True, verbose_name="パスワード")
    
    # 抽出設定
    extraction_selectors = models.TextField(verbose_name="抽出セレクタ（JSON形式）")
    use_text_mode = models.BooleanField(default=False, verbose_name="文字列モード")
    
    # ページネーション設定
    use_pagination = models.BooleanField(default=False, verbose_name="ページネーションを使用")
    next_button_selector = models.CharField(max_length=255, blank=True, null=True, verbose_name="次へボタンセレクタ")
    max_pages = models.IntegerField(default=1, verbose_name="最大ページ数")
    
    # 画像ダウンロード設定
    download_images = models.BooleanField(default=False, verbose_name="画像をダウンロード")
    image_selector = models.CharField(max_length=255, blank=True, null=True, verbose_name="画像セレクタ")
    
    # 出力設定
    output_path = models.CharField(max_length=255, default='output', verbose_name="出力パス")
    
    def get_urls(self):
        """JSON形式のURLをリストに変換"""
        try:
            return json.loads(self.urls)
        except:
            return []
    
    def get_extraction_selectors(self):
        """JSON形式の抽出セレクタを辞書に変換"""
        try:
            return json.loads(self.extraction_selectors)
        except:
            return {}
    
    def __str__(self):
        return self.name 