import time
import schedule
import logging
import sys
import os
from datetime import datetime

# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data_collector import FinanceNewsCollector

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoNewsCollector:
    def __init__(self):
        self.collector = FinanceNewsCollector()
        self.is_running = False

    def collect_news_job(self):
        """Задача по сбору новостей"""
        try:
            logger.info("🚀 ЗАПУСК АВТОМАТИЧЕСКОГО СБОРА НОВОСТЕЙ")
            
            articles = self.collector.collect_news(hours_back=24)
            
            logger.info(f"✅ АВТОСБОР ЗАВЕРШЕН. Собрано {len(articles)} финансовых статей")
            
            # Логируем статистику
            self.log_statistics()
            
        except Exception as e:
            logger.error(f"❌ ОШИБКА АВТОСБОРА: {e}")

    def log_statistics(self):
        """Логирование статистики базы данных"""
        try:
            import sqlite3
            conn = sqlite3.connect("data/news.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM raw_articles WHERE is_finance = 1")
            total_finance = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT source_name, COUNT(*) 
                FROM raw_articles 
                WHERE is_finance = 1 
                GROUP BY source_name
            """)
            sources_stats = cursor.fetchall()
            
            conn.close()
            
            logger.info(f"📊 СТАТИСТИКА БАЗЫ: Всего финансовых статей: {total_finance}")
            for source, count in sources_stats:
                logger.info(f"  {source}: {count} статей")
                
        except Exception as e:
            logger.error(f"Ошибка при логировании статистики: {e}")

    def run_immediately(self):
        """Немедленный запуск сбора"""
        logger.info("▶️ НЕМЕДЛЕННЫЙ ЗАПУСК СБОРА")
        self.collect_news_job()

    def start_scheduler(self):
        """Запуск планировщика"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return

        logger.info("⏰ ЗАПУСК ПЛАНИРОВЩИКА СБОРА НОВОСТЕЙ")
        
        # Расписание сбора новостей
        schedule.every(30).minutes.do(self.collect_news_job)  # Каждые 30 минут
        schedule.every(1).hour.do(self.collect_news_job)      # Каждый час
        schedule.every().day.at("08:00").do(self.collect_news_job)  # Утром
        schedule.every().day.at("12:00").do(self.collect_news_job)  # В обед
        schedule.every().day.at("18:00").do(self.collect_news_job)  # Вечером
        
        self.is_running = True
        
        logger.info("📅 РАСПИСАНИЕ УСТАНОВЛЕНО:")
        logger.info("  - Каждые 30 минут")
        logger.info("  - Каждый час") 
        logger.info("  - В 08:00, 12:00, 18:00 ежедневно")
        
        # Немедленный запуск первого сбора
        self.run_immediately()
        
        # Бесконечный цикл планировщика
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверка каждую минуту
            except KeyboardInterrupt:
                logger.info("🛑 ОСТАНОВКА ПЛАНИРОВЩИКА ПО ЗАПРОСУ ПОЛЬЗОВАТЕЛЯ")
                break
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                time.sleep(300)  # Ждем 5 минут при ошибке

    def stop_scheduler(self):
        """Остановка планировщика"""
        self.is_running = False
        logger.info("🛑 ПЛАНИРОВЩИК ОСТАНОВЛЕН")

def main():
    """Основная функция"""
    print("=" * 60)
    print("📡 RADAR - АВТОМАТИЧЕСКИЙ СБОРЩИК ФИНАНСОВЫХ НОВОСТЕЙ")
    print("=" * 60)
    print("Режимы работы:")
    print("  1. Однократный сбор (запуск и выход)")
    print("  2. Фоновый режим (постоянный сбор по расписанию)")
    print("  3. Только планировщик (без немедленного сбора)")
    print()
    
    try:
        mode = input("Выберите режим (1/2/3, по умолчанию 1): ").strip()
        
        collector = AutoNewsCollector()
        
        if mode == "2":
            print("🚀 ЗАПУСК В ФОНОВОМ РЕЖИМЕ...")
            collector.start_scheduler()
        elif mode == "3":
            print("⏰ ЗАПУСК ТОЛЬКО ПЛАНИРОВЩИКА...")
            collector.is_running = True
            collector.start_scheduler()
        else:
            print("⚡ ОДНОКРАТНЫЙ СБОР...")
            collector.run_immediately()
            print("✅ СБОР ЗАВЕРШЕН")
            
    except KeyboardInterrupt:
        print("\n🛑 ВЫХОД ПО ЗАПРОСУ ПОЛЬЗОВАТЕЛЯ")
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == "__main__":
    main()