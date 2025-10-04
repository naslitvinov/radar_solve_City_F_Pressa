import json
import requests
import sqlite3
import os
from datetime import datetime, timedelta
import time
import logging
from bs4 import BeautifulSoup
import hashlib
import re
import urllib3
import feedparser
import asyncio
import aiohttp
from urllib.parse import urljoin
import random

# Отключение предупреждений SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedFinanceNewsCollector:
    def __init__(self, config_path="config/sources.json", db_path="data/news.db"):
        self.config_path = config_path
        self.db_path = db_path
        self.sources_config = self._load_config()
        self.session = None
        self._setup_directories()
        self._setup_database()

        # Расширенные финансовые ключевые слова на разных языках
        self.finance_keywords = [
            # Russian
            'финанс', 'экономик', 'бизнес', 'рынок', 'акци', 'облигаци', 'инвест', 'банк',
            'курс', 'доллар', 'евро', 'рубл', 'бирж', 'трейд', 'капитал', 'дивиденд',
            'прибыль', 'убыток', 'бюджет', 'налог', 'инфляц', 'ввп', 'IPO', 'SPO',
            'санкц', 'нефть', 'газ', 'энергетик', 'металл', 'золот', 'серебр',
            'крипто', 'биткоин', 'блокчейн', 'майнинг', 'трейд', 'трейдер',
            
            # English
            'finance', 'economy', 'business', 'market', 'stock', 'bond', 'investment', 'bank',
            'currency', 'dollar', 'euro', 'ruble', 'exchange', 'trade', 'capital', 'dividend',
            'profit', 'loss', 'budget', 'tax', 'inflation', 'gdp', 'IPO', 'offering',
            'sanction', 'oil', 'gas', 'energy', 'metal', 'gold', 'silver',
            'crypto', 'bitcoin', 'blockchain', 'mining', 'trader', 'trading'
        ]

        # User-Agents для обхода блокировок
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Конфигурационный файл {self.config_path} не найден")
            return {"html_sources": [], "rss_sources": []}

    def _setup_directories(self):
        os.makedirs("data", exist_ok=True)
        os.makedirs("config", exist_ok=True)

    def _setup_database(self):
        """Настройка базы данных с улучшенной структурой"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_articles (
                    id TEXT PRIMARY KEY,
                    source_name TEXT,
                    title TEXT,
                    url TEXT,
                    content TEXT,
                    published_at TIMESTAMP,
                    collected_at TIMESTAMP,
                    language TEXT,
                    category TEXT,
                    is_finance BOOLEAN DEFAULT 0,
                    country TEXT DEFAULT 'unknown',
                    importance_score REAL DEFAULT 0.5
                )
            ''')
            
            # Создаем индекс для быстрого поиска
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_finance_published 
                ON raw_articles(is_finance, published_at)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ База данных инициализирована с улучшенной структурой")
        except Exception as e:
            logger.error(f"❌ Ошибка создания базы данных: {e}")

    def get_random_user_agent(self):
        """Возвращает случайный User-Agent"""
        return random.choice(self.user_agents)

    async def collect_news_async(self, hours_back=48):
        """Улучшенный сбор новостей с поддержкой международных источников"""
        logger.info("🚀 ЗАПУСК РАСШИРЕННОГО СБОРА ФИНАНСОВЫХ НОВОСТЕЙ")
        
        all_articles = []
        
        # Собираем из HTML источников
        logger.info("📄 Сбор из HTML источников...")
        html_articles = await self.parse_html_sources_async()
        all_articles.extend(html_articles)
        
        # Собираем из RSS источников
        logger.info("📡 Сбор из RSS источников...")
        rss_articles = await self.parse_rss_sources_async()
        all_articles.extend(rss_articles)

        # Обрабатываем и обогащаем статьи
        logger.info("🔧 Обработка и обогащение статей...")
        enriched_articles = await self.enrich_articles_async(all_articles)

        # Сохраняем в базу
        saved_count = await self.save_to_database_async(enriched_articles)
        
        logger.info(f"✅ СБОР ЗАВЕРШЕН. Обработано статей: {len(all_articles)}, Сохранено финансовых: {saved_count}")
        return enriched_articles

    async def parse_html_sources_async(self):
        """Асинхронный парсинг HTML источников с улучшенной обработкой"""
        articles = []
        semaphore = asyncio.Semaphore(5)  # Ограничиваем одновременные запросы
        
        async def process_source(source):
            async with semaphore:
                if source.get('type') != 'html':
                    return []
                
                try:
                    logger.info(f"Парсинг HTML {source['name']}...")
                    
                    headers = {
                        'User-Agent': self.get_random_user_agent(),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                    
                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(source['url'], timeout=30, ssl=False) as response:
                            if response.status != 200:
                                logger.warning(f"Статус {response.status} для {source['name']}")
                                return []
                            
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            selectors = source.get('selectors', {})
                            
                            source_articles = []
                            article_selector = selectors.get('article', '')
                            
                            if article_selector:
                                article_elements = soup.select(article_selector)
                                logger.info(f"Найдено элементов в {source['name']}: {len(article_elements)}")
                                
                                for elem in article_elements[:15]:  # Ограничиваем количество
                                    article_data = self._extract_article_data(elem, selectors, source)
                                    if article_data:
                                        source_articles.append(article_data)
                            
                            # Задержка для избежания блокировки
                            await asyncio.sleep(1)
                            return source_articles
                            
                except Exception as e:
                    logger.error(f"Ошибка при парсинге HTML {source['name']}: {e}")
                    return []
        
        # Запускаем все источники параллельно
        tasks = [process_source(source) for source in self.sources_config.get("html_sources", [])]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем все статьи
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
        
        return articles

    async def parse_rss_sources_async(self):
        """Асинхронный парсинг RSS источников с поддержкой международных"""
        articles = []
        semaphore = asyncio.Semaphore(10)  # RSS запросы быстрее, можно больше
        
        async def process_source(source):
            async with semaphore:
                if source.get('type') != 'rss':
                    return []
                
                try:
                    logger.info(f"Парсинг RSS {source['name']}...")
                    
                    # Используем feedparser в отдельном потоке
                    def parse_feed():
                        return feedparser.parse(source['url'])
                    
                    feed = await asyncio.get_event_loop().run_in_executor(None, parse_feed)
                    
                    if hasattr(feed, 'status') and feed.status != 200:
                        logger.warning(f"RSS статус {feed.status} для {source['name']}")
                        return []
                    
                    source_articles = []
                    entries = feed.entries[:20]  # Ограничиваем количество
                    
                    logger.info(f"Найдено RSS элементов в {source['name']}: {len(entries)}")
                    
                    for entry in entries:
                        article_data = self._extract_rss_article_data(entry, source)
                        if article_data:
                            source_articles.append(article_data)
                    
                    # Короткая задержка
                    await asyncio.sleep(0.5)
                    return source_articles
                    
                except Exception as e:
                    logger.error(f"Ошибка при парсинге RSS {source['name']}: {e}")
                    return []
        
        # Запускаем все RSS источники параллельно
        tasks = [process_source(source) for source in self.sources_config.get("rss_sources", [])]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем все статьи
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
        
        return articles

    def _extract_article_data(self, elem, selectors, source):
        """Улучшенное извлечение данных статьи из HTML элемента"""
        try:
            # Извлечение заголовка
            title_elem = elem.select_one(selectors.get('title', '')) if selectors.get('title') else elem
            title = title_elem.get_text().strip() if title_elem else ''
            
            if not title or len(title) < 10:
                return None

            # Извлечение ссылки
            link_elem = None
            if selectors.get('link'):
                link_elem = elem.select_one(selectors.get('link', ''))
            
            if not link_elem:
                link_elem = elem.find('a') if hasattr(elem, 'find') else None
            
            if not link_elem or not link_elem.get('href'):
                return None
            
            url = link_elem.get('href', '')
            url = self._parse_relative_url(url, source['url'])

            # Фильтрация нежелательных ссылок
            skip_keywords = ['facebook', 'twitter', 'instagram', 'vk.com', 'telegram', 
                           'youtube', 'login', 'signin', 'advertisement', 'ads']
            if any(keyword in url.lower() for keyword in skip_keywords):
                return None

            # Извлечение контента
            content = ""
            if selectors.get('summary'):
                content_elem = elem.select_one(selectors.get('summary', ''))
                if content_elem:
                    content = content_elem.get_text().strip()

            # Извлечение времени
            published_at = datetime.now()
            if selectors.get('time'):
                time_elem = elem.select_one(selectors.get('time', ''))
                if time_elem:
                    time_text = time_elem.get_text().strip()
                    published_at = self._parse_time(time_text, source.get('language', 'ru'))

            # Определение страны и языка
            language = source.get('language', self._detect_language(title))
            country = self._detect_country(source['name'], language)

            # Создание статьи
            article_id = hashlib.md5(f"{title}{url}".encode()).hexdigest()
            
            article_data = {
                'id': article_id,
                'source_name': source['name'],
                'title': title,
                'url': url,
                'content': content,
                'published_at': published_at,
                'collected_at': datetime.now(),
                'language': language,
                'category': 'finance',
                'is_finance': True,
                'country': country,
                'importance_score': self._calculate_importance_score(title, content, source['name'])
            }
            
            return article_data
            
        except Exception as e:
            logger.debug(f"Ошибка извлечения данных статьи: {e}")
            return None

    def _extract_rss_article_data(self, entry, source):
        """Улучшенное извлечение данных из RSS элемента"""
        try:
            title = entry.get('title', '').strip()
            if not title:
                return None

            link = entry.get('link', '')
            if not link:
                return None

            # Извлекаем содержание
            content = ''
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
            elif hasattr(entry, 'content'):
                if hasattr(entry.content[0], 'value'):
                    content = entry.content[0].value

            # Парсим время публикации
            published_at = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_at = datetime(*entry.updated_parsed[:6])

            # Определяем язык и страну
            language = source.get('language', self._detect_language(title))
            country = self._detect_country(source['name'], language)

            # Создаем ID статьи
            article_id = hashlib.md5(f"{title}{link}".encode()).hexdigest()

            article_data = {
                'id': article_id,
                'source_name': source['name'],
                'title': title,
                'url': link,
                'content': content,
                'published_at': published_at,
                'collected_at': datetime.now(),
                'language': language,
                'category': 'finance',
                'is_finance': True,
                'country': country,
                'importance_score': self._calculate_importance_score(title, content, source['name'])
            }

            return article_data
            
        except Exception as e:
            logger.debug(f"Ошибка извлечения RSS данных: {e}")
            return None

    def _parse_relative_url(self, url, base_url):
        """Парсинг относительных URL"""
        if url.startswith('http'):
            return url
        elif url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            base = '/'.join(base_url.split('/')[:3])
            return base + url
        else:
            return urljoin(base_url, url)

    def _parse_time(self, time_text, language='ru'):
        """Парсинг времени из текста"""
        try:
            # Простой парсинг для демо - в реальном проекте нужно улучшить
            if 'hour' in time_text.lower() or 'час' in time_text.lower():
                hours = int(re.search(r'(\d+)', time_text).group(1))
                return datetime.now() - timedelta(hours=hours)
            elif 'minute' in time_text.lower() or 'минут' in time_text.lower():
                minutes = int(re.search(r'(\d+)', time_text).group(1))
                return datetime.now() - timedelta(minutes=minutes)
            elif 'day' in time_text.lower() or 'день' in time_text.lower() or 'дн' in time_text.lower():
                days = int(re.search(r'(\d+)', time_text).group(1))
                return datetime.now() - timedelta(days=days)
            else:
                return datetime.now()
        except:
            return datetime.now()

    def _detect_language(self, text):
        """Определение языка текста"""
        if not text:
            return 'unknown'
        
        text_lower = text.lower()
        
        # Проверяем наличие кириллицы
        cyrillic_count = sum(1 for char in text if 'а' <= char <= 'я' or 'А' <= char <= 'Я')
        latin_count = sum(1 for char in text if 'a' <= char <= 'z' or 'A' <= char <= 'Z')
        
        if cyrillic_count > latin_count:
            return 'ru'
        elif latin_count > cyrillic_count:
            return 'en'
        else:
            return 'unknown'

    def _detect_country(self, source_name, language):
        """Определение страны на основе источника и языка"""
        source_lower = source_name.lower()
        
        if any(word in source_lower for word in ['reuters', 'bloomberg', 'cnbc', 'financial times', 
                                               'marketwatch', 'yahoo', 'bbc', 'cnn', 'wall street']):
            return 'usa'
        elif any(word in source_lower for word in ['рбк', 'коммерсант', 'ведомости', 'тасс', 
                                                 'интерфакс', 'прайм', 'финам', 'банки.ру']):
            return 'russia'
        elif language == 'ru':
            return 'russia'
        elif language == 'en':
            return 'usa'
        else:
            return 'international'

    def _calculate_importance_score(self, title, content, source_name):
        """Расчет важности статьи"""
        text = f"{title} {content}".lower()
        score = 0.3
        
        # Вес источника
        source_weights = {
            'reuters': 0.9, 'bloomberg': 0.95, 'financial times': 0.9,
            'рбк': 0.85, 'коммерсант': 0.8, 'ведомости': 0.8,
            'цб': 1.0, 'ecb': 0.9, 'imf': 0.9, 'world bank': 0.9
        }
        
        for source, weight in source_weights.items():
            if source in source_name.lower():
                score = weight
                break
        
        # Ключевые слова для увеличения важности
        important_terms = {
            'срочн': 0.2, 'экстрен': 0.3, 'кризис': 0.25, 'важн': 0.15,
            'urgent': 0.2, 'breaking': 0.3, 'crisis': 0.25, 'important': 0.15,
            'санкц': 0.2, 'санкции': 0.2, 'sanction': 0.2,
            'цб': 0.3, 'central bank': 0.3, 'fed': 0.3,
            'курс': 0.15, 'exchange rate': 0.15, 'currency': 0.15,
            'нефть': 0.2, 'oil': 0.2, 'газ': 0.2, 'gas': 0.2,
            'биткоин': 0.15, 'bitcoin': 0.15, 'крипто': 0.15, 'crypto': 0.15
        }
        
        for term, boost in important_terms.items():
            if term in text:
                score += boost
                break  # Только одно самое важное слово
        
        return min(max(score, 0.1), 1.0)

    def _is_finance_article(self, title, content):
        """Проверка финансовой тематики с улучшенной логикой"""
        text = (title + ' ' + content).lower()
        
        # Считаем совпадения с финансовыми ключевыми словами
        finance_matches = sum(1 for keyword in self.finance_keywords if keyword in text)
        
        # Более гибкие условия для международных новостей
        if finance_matches >= 1:  # Уменьшили порог для большего охвата
            return True
            
        # Дополнительные проверки для специфических терминов
        specific_terms = ['ruble', 'rubl', 'mosprime', 'moex', 'rts', 'russian market']
        if any(term in text for term in specific_terms):
            return True
            
        return False

    async def enrich_articles_async(self, articles):
        """Обогащение статей дополнительной информацией"""
        enriched = []
        
        for article in articles:
            try:
                # Определяем категорию на основе контента
                category = self._categorize_article(article['title'], article.get('content', ''))
                article['category'] = category
                
                # Добавляем теги
                article['tags'] = self._extract_tags(article['title'], article.get('content', ''))
                
                # Улучшаем оценку важности
                article['importance_score'] = self._calculate_importance_score(
                    article['title'], article.get('content', ''), article['source_name']
                )
                
                enriched.append(article)
                
            except Exception as e:
                logger.error(f"Ошибка обогащения статьи: {e}")
                enriched.append(article)  # Все равно добавляем статью
        
        return enriched

    def _categorize_article(self, title, content):
        """Категоризация статьи"""
        text = (title + ' ' + content).lower()
        
        categories = {
            'stocks': ['акци', 'stock', 'equity', 'shares', 'бирж', 's&p', 'dow', 'nasdaq'],
            'bonds': ['облигац', 'bond', 'debt', 'coupon', 'yield'],
            'currency': ['курс', 'currency', 'dollar', 'euro', 'рубл', 'ruble', 'exchange rate'],
            'commodities': ['нефть', 'oil', 'газ', 'gas', 'золот', 'gold', 'металл', 'metal'],
            'crypto': ['крипто', 'crypto', 'биткоин', 'bitcoin', 'блокчейн', 'blockchain'],
            'banking': ['банк', 'bank', 'кредит', 'credit', 'ставк', 'interest rate'],
            'regulation': ['регулирован', 'regulation', 'санкц', 'sanction', 'цб', 'central bank'],
            'macro': ['ввп', 'gdp', 'инфляц', 'inflation', 'экономик', 'economy']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'general'

    def _extract_tags(self, title, content):
        """Извлечение тегов из статьи"""
        text = (title + ' ' + content).lower()
        tags = set()
        
        # Ключевые компании и организации
        entities = [
            'сбербанк', 'sberbank', 'газпром', 'gazprom', 'роснефть', 'rosneft', 
            'лукойл', 'lukoil', 'втб', 'vtb', 'яндекс', 'yandex', 'тинькофф', 'tinkoff',
            'apple', 'microsoft', 'google', 'amazon', 'tesla', 'meta', 'facebook'
        ]
        
        for entity in entities:
            if entity in text:
                tags.add(entity)
        
        # Общие темы
        themes = ['рынок', 'market', 'инвест', 'invest', 'трейд', 'trade', 'финанс', 'finance']
        for theme in themes:
            if theme in text:
                tags.add(theme)
        
        return list(tags)[:5]  # Ограничиваем количество тегов

    async def save_to_database_async(self, articles):
        """Асинхронное сохранение в базу данных с улучшенной логикой"""
        if not articles:
            logger.info("❌ Нет статей для сохранения")
            return 0

        try:
            def save_sync():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                saved_count = 0
                
                for article in articles:
                    try:
                        # Проверяем, финансовая ли это статья
                        is_finance = self._is_finance_article(article['title'], article.get('content', ''))
                        article['is_finance'] = is_finance
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO raw_articles
                            (id, source_name, title, url, content, published_at, collected_at, 
                             language, category, is_finance, country, importance_score)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            article['id'],
                            article['source_name'],
                            article['title'],
                            article['url'],
                            article['content'],
                            article['published_at'].isoformat(),
                            article['collected_at'].isoformat(),
                            article['language'],
                            article['category'],
                            article['is_finance'],
                            article.get('country', 'unknown'),
                            article.get('importance_score', 0.5)
                        ))
                        
                        if cursor.rowcount > 0:
                            saved_count += 1
                            if saved_count % 10 == 0:
                                logger.info(f"💾 Сохранено {saved_count} статей...")
                                
                    except Exception as e:
                        logger.error(f"❌ ОШИБКА СОХРАНЕНИЯ: {e}")
                        continue

                conn.commit()
                conn.close()
                return saved_count
            
            # Запускаем в отдельном потоке
            saved_count = await asyncio.get_event_loop().run_in_executor(None, save_sync)
            logger.info(f"💾 В БАЗУ СОХРАНЕНО: {saved_count} статей")
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ ОШИБКА БАЗЫ ДАННЫХ: {e}")
            return 0

    async def get_collection_stats(self):
        """Получение статистики по сбору"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute("SELECT COUNT(*) FROM raw_articles WHERE is_finance = 1")
            total_finance = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(DISTINCT source_name) FROM raw_articles WHERE is_finance = 1")
            sources_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM raw_articles WHERE is_finance = 1 AND datetime(collected_at) > datetime('now', '-1 day')")
            last_24h = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT country, COUNT(*) FROM raw_articles WHERE is_finance = 1 GROUP BY country")
            countries_stats = cursor.fetchall()
            
            cursor.execute("SELECT language, COUNT(*) FROM raw_articles WHERE is_finance = 1 GROUP BY language")
            languages_stats = cursor.fetchall()
            
            conn.close()
            
            stats = {
                'total_finance_articles': total_finance,
                'sources_count': sources_count,
                'last_24h_articles': last_24h,
                'countries': dict(countries_stats),
                'languages': dict(languages_stats)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}

def main():
    """Основная функция с улучшенной статистикой"""
    async def run_collection():
        collector = AdvancedFinanceNewsCollector()
        
        print("🌐 ЗАПУСК РАСШИРЕННОГО СБОРА НОВОСТЕЙ")
        print("=" * 60)
        
        # Запускаем сбор
        articles = await collector.collect_news_async(hours_back=48)
        
        # Получаем статистику
        stats = await collector.get_collection_stats()
        
        # Выводим подробную статистику
        print(f"\n📊 ДЕТАЛЬНАЯ СТАТИСТИКА СБОРА")
        print("=" * 60)
        print(f"📈 Всего финансовых статей в базе: {stats.get('total_finance_articles', 0)}")
        print(f"📰 Источников: {stats.get('sources_count', 0)}")
        print(f"🕐 За последние 24 часа: {stats.get('last_24h_articles', 0)}")
        
        print(f"\n🌍 РАСПРЕДЕЛЕНИЕ ПО СТРАНАМ:")
        for country, count in stats.get('countries', {}).items():
            print(f"   {country}: {count} статей")
            
        print(f"\n🗣️ РАСПРЕДЕЛЕНИЕ ПО ЯЗЫКАМ:")
        for language, count in stats.get('languages', {}).items():
            print(f"   {language}: {count} статей")
        
        if articles:
            print(f"\n📰 ПОСЛЕДНИЕ ФИНАНСОВЫЕ СТАТЬИ:")
            for i, article in enumerate(articles[:5], 1):
                print(f"\n{i}. [{article['source_name']}] [{article.get('country', 'unknown')}]")
                print(f"   📝 {article['title']}")
                print(f"   🔗 {article['url']}")
                print(f"   ⭐ Важность: {article.get('importance_score', 0.5):.2f}")
                if article.get('tags'):
                    print(f"   🏷️ Теги: {', '.join(article['tags'][:3])}")
        else:
            print("\n❌ В этом запуске не собрано финансовых статей")
            
        print(f"\n✅ Сбор завершен успешно!")

    asyncio.run(run_collection())

if __name__ == "__main__":
    main()