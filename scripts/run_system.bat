@echo off
chcp 65001 > nul
title RADAR - Система мониторинга финансовых новостей

echo ========================================
echo    📡 RADAR FINANCIAL MONITORING SYSTEM
echo ========================================
echo.
echo Система работает с реальными данными
echo.
echo Доступные команды:
echo   1 - Запуск веб-интерфейса
echo   2 - Запуск сборщика новостей
echo   3 - Проверка статуса базы данных
echo.

set /p choice="Выберите команду (1/2/3): "

if "%choice%"=="1" (
    echo 🌐 Запуск веб-интерфейса...
    python app.py
) else if "%choice%"=="2" (
    echo 🚀 Запуск сборщика новостей...
    python data_collector.py
) else if "%choice%"=="3" (
    echo 📊 Проверка статуса системы...
    python -c "
import sqlite3
import os
from datetime import datetime

def check_database():
    if not os.path.exists('data/news.db'):
        print('❌ База данных не найдена')
        return
        
    conn = sqlite3.connect('data/news.db')
    cursor = conn.cursor()
    
    # Проверяем таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_articles'")
    if not cursor.fetchone():
        print('❌ Таблица новостей не найдена')
        return
        
    # Статистика
    cursor.execute('SELECT COUNT(*) FROM raw_articles WHERE is_finance=1')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT source_name) FROM raw_articles WHERE is_finance=1')
    sources = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM raw_articles WHERE is_finance=1 AND datetime(collected_at) > datetime("now", "-1 day")')
    last_24h = cursor.fetchone()[0]
    
    print(f'✅ База данных в порядке')
    print(f'📊 Всего финансовых статей: {total}')
    print(f'📰 Источников: {sources}')
    print(f'🕐 За последние 24 часа: {last_24h}')
    
    conn.close()

check_database()
"
) else (
    echo ❌ Неверный выбор
)

pause