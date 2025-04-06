@echo off
echo MaxWell Webscraper を起動しています...
echo.

REM 正しいディレクトリに移動
cd MaxWell_Webscraper

REM 仮想環境のアクティベート
echo 仮想環境をアクティベートしています...
call ..\venv\Scripts\activate.bat

REM 必要なパッケージのインストール
echo 必要なパッケージをインストールしています...
pip install django selenium pandas webdriver-manager

REM サーバーの起動
echo Djangoサーバーを起動します...
python manage.py runserver

REM エラーが発生した場合にウィンドウを閉じないようにする
pause 