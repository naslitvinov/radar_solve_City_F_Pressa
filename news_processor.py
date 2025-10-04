import sqlite3
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)

class NewsProcessor:
    def __init__(self, db_path="data/news.db"):
        self.db_path = db_path
    
    def get_recent_news(self, hours=24, limit=10):
        """Получение последних новостей из базы"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT id, source_name, title, url, content, published_at, collected_at 
                FROM raw_articles 
                WHERE published_at >= ? AND is_finance = 1
                ORDER BY published_at DESC
                LIMIT ?
            ''', (since_time.isoformat(), limit))
            
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    'id': row[0],
                    'source_name': row[1],
                    'title': row[2],
                    'url': row[3],
                    'content': row[4],
                    'published_at': datetime.fromisoformat(row[5]),
                    'collected_at': datetime.fromisoformat(row[6])
                })
            
            conn.close()
            return articles
        except Exception as e:
            logger.error(f"Ошибка при получении новостей: {e}")
            return []
    
    def calculate_hotness(self, article):
        """Расчет показателя горячести для статьи"""
        score = 0.5
        
        # Веса источников
        source_scores = {
            'РБК': 0.9,
            'Reuters': 0.95,
            'Коммерсант': 0.85,
            'Интерфакс': 0.8
        }
        
        for source, weight in source_scores.items():
            if source in article['source_name']:
                score = weight
                break
        
        return min(max(score, 0.1), 0.99)
    
    def process_news_batch(self, articles):
        """Обработка батча новостей"""
        processed = []
        
        for article in articles:
            processed.append({
                'id': hashlib.md5(article['title'].encode()).hexdigest()[:8],
                'headline': article['title'],
                'hotness': self.calculate_hotness(article),
                'source': article['source_name'],
                'url': article['url'],
                'content': article['content'],
                'timestamp': article['published_at']
            })
        
        return sorted(processed, key=lambda x: x['hotness'], reverse=True)