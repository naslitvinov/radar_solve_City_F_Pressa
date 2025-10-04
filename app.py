from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime, timedelta
import sqlite3
import logging
import os
import threading
import time
import asyncio
import queue
import hashlib

app = Flask(__name__)
app.secret_key = 'radar-secret-key-2025'

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные
components_ready = False
collector = None
neural_analyzer = None
news_drafts = {}
initial_collection_done = False

# Очереди для фоновой обработки
news_processing_queue = queue.Queue()
processing_results = {}
background_processor = None

def initialize_components():
    """Инициализация компонентов системы"""
    global components_ready, collector, neural_analyzer, background_processor
    
    try:
        logger.info("🔄 Инициализация компонентов системы...")
        
        #  создаем базу данных
        setup_database()
        
        
        from data_collector import AdvancedFinanceNewsCollector
        collector = AdvancedFinanceNewsCollector()
        logger.info("✅ Коллектор новостей инициализирован")
        
        def init_neural_in_background():
            global neural_analyzer
            try:
                from neural_analyzer import NeuralNewsAnalyzer
                neural_analyzer = NeuralNewsAnalyzer()
                neural_status = neural_analyzer.get_models_status()
                logger.info(f"🧠 Нейросетевой анализатор: {neural_status}")
                
                if neural_analyzer.models_loaded:
                    start_background_processor()
                    
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации нейросетей: {e}")
                neural_analyzer = None
        
        neural_thread = threading.Thread(target=init_neural_in_background)
        neural_thread.daemon = True
        neural_thread.start()
        
        # Сразу создаем демо-данные
        create_demo_data_if_needed()
        
        components_ready = True
        logger.info("✅ Все компоненты инициализированы")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации компонентов: {e}")
        components_ready = False

def start_background_processor():
    """Запускает фоновый процессор для нейросетевой обработки"""
    global background_processor
    
    if background_processor and background_processor.is_alive():
        return
    
    def process_news_background():
        """Фоновая обработка новостей нейросетями"""
        while True:
            try:
                # Берем новость из очереди (с таймаутом чтобы не блокировать)
                try:
                    news_data = news_processing_queue.get(timeout=1.0)
                    news_id, article = news_data
                    
                    logger.info(f"🧠 Фоновая обработка новости: {article['title'][:50]}...")
                    
                    # Обрабатываем нейросетью
                    if neural_analyzer and neural_analyzer.models_loaded:
                        processed_articles = asyncio.run(
                            neural_analyzer.process_articles_batch([article])
                        )
                        
                        if processed_articles:
                            enhanced_article = processed_articles[0]
                            
                            # Сохраняем результат
                            processing_results[news_id] = {
                                'enhanced_data': enhanced_article,
                                'processed_at': datetime.now(),
                                'status': 'completed'
                            }
                            
                            # Обновляем базу данных с улучшенными данными
                            update_article_with_ai_data(news_id, enhanced_article)
                            
                            logger.info(f"✅ Новость обработана нейросетью: {news_id}")
                    
                    news_processing_queue.task_done()
                    
                except queue.Empty:
                    # Очередь пуста, продолжаем ждать
                    time.sleep(0.1)
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Ошибка фоновой обработки: {e}")
                time.sleep(1)
    
    background_processor = threading.Thread(target=process_news_background)
    background_processor.daemon = True
    background_processor.start()
    logger.info("✅ Фоновый процессор нейросетей запущен")

def update_article_with_ai_data(article_id, enhanced_data):
    """Обновляет статью в базе с AI-данными"""
    try:
        conn = sqlite3.connect('data/news.db')
        cursor = conn.cursor()
        
        # Создаем таблицу для АИ данных
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_article_data (
                article_id TEXT PRIMARY KEY,
                enhanced_data TEXT,
                processed_at TIMESTAMP,
                ai_enhanced BOOLEAN DEFAULT 1
            )
        ''')
        
        # Сохраняем улучшенные данные
        cursor.execute('''
            INSERT OR REPLACE INTO ai_article_data 
            (article_id, enhanced_data, processed_at, ai_enhanced)
            VALUES (?, ?, ?, ?)
        ''', (
            article_id,
            json.dumps(enhanced_data, ensure_ascii=False),
            datetime.now().isoformat(),
            True
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения AI-данных: {e}")

def get_ai_enhanced_data(article_id):
    """Получает AI-улучшенные данные для статьи"""
    try:
        conn = sqlite3.connect('data/news.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT enhanced_data FROM ai_article_data 
            WHERE article_id = ? AND ai_enhanced = 1
        ''', (article_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения AI-данных: {e}")
        return None

def setup_database():
    """Создает базу данных с правильной структурой"""
    try:
        os.makedirs('data', exist_ok=True)
        
        conn = sqlite3.connect('data/news.db')
        cursor = conn.cursor()
        
        # Основная таблица 
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_article_data (
                article_id TEXT PRIMARY KEY,
                enhanced_data TEXT,
                processed_at TIMESTAMP,
                ai_enhanced BOOLEAN DEFAULT 1
            )
        ''')
        
        # Проверяем и добавляем отсутствующие колонки
        cursor.execute("PRAGMA table_info(raw_articles)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        required_columns = ['country', 'importance_score']
        for column in required_columns:
            if column not in existing_columns:
                if column == 'country':
                    cursor.execute("ALTER TABLE raw_articles ADD COLUMN country TEXT DEFAULT 'unknown'")
                elif column == 'importance_score':
                    cursor.execute("ALTER TABLE raw_articles ADD COLUMN importance_score REAL DEFAULT 0.5")
                logger.info(f"✅ Добавлена колонка: {column}")
        
        # Создаем индексы 
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_finance_published 
            ON raw_articles(is_finance, published_at)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ai_processed 
            ON ai_article_data(processed_at)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания базы данных: {e}")

def get_real_news_from_db(hours=24, limit=50, sort_by='hotness', priority_filter='all'):
    """Получение новостей из базы с поддержкой сортировки и фильтрации"""
    try:
        if not os.path.exists('data/news.db'):
            return []
            
        conn = sqlite3.connect('data/news.db')
        cursor = conn.cursor()
        
        since_time = datetime.now() - timedelta(hours=hours)
        #БАЗА SQL ЗАПРОСА 
        base_query = '''
            SELECT id, source_name, title, url, content, published_at, country, importance_score
            FROM raw_articles 
            WHERE is_finance = 1 AND published_at >= ?
        '''
        
        # Добавляем фильтр по приоритету
        params = [since_time.isoformat()]
        
        priority_conditions = {
            'high': 'importance_score > 0.7',
            'medium': 'importance_score BETWEEN 0.4 AND 0.7', 
            'low': 'importance_score < 0.4',
            'all': '1=1'
        }
        
        if priority_filter in priority_conditions:
            base_query += f' AND {priority_conditions[priority_filter]}'
        
        # Добавляем сортировку
        sort_options = {
            'hotness': 'importance_score DESC',
            'date_new': 'published_at DESC',
            'date_old': 'published_at ASC',
            'source': 'source_name ASC'
        }
        
        order_by = sort_options.get(sort_by, 'importance_score DESC')
        base_query += f' ORDER BY {order_by}'
        
        # 
        base_query += ' LIMIT ?'
        params.append(limit)
        
        cursor.execute(base_query, params)
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0],
                'source_name': row[1],
                'title': row[2],
                'url': row[3],
                'content': row[4] or '',
                'published_at': datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                'country': row[6] or 'unknown',
                'importance_score': row[7] or 0.5,
                'collected_at': datetime.now()
            })
        
        conn.close()
        return articles
        
    except Exception as e:
        logger.error(f"Ошибка при получении новостей из базы: {e}")
        return []

def quick_entity_extraction(title):
    """Быстрое извлечение сущностей"""
    text_lower = title.lower()
    entities = []
    
    company_keywords = ['сбербанк', 'газпром', 'роснефть', 'лукойл', 'втб', 'яндекс',
                       'тинькофф', 'альфа-банк', 'мосбиржа', 'цб', 'минфин']
    
    for company in company_keywords:
        if company in text_lower:
            entities.append(company.title())
    
    return entities[:4] or ['Финансы']

def quick_draft_generation(title, entities):
    """Быстрая генерация черновика"""
    main_entity = entities[0] if entities else 'рынка'
    
    return {
        'title': f"Анализ: {title}",
        'lead': f"Событие привлекает внимание финансового сообщества.",
        'bullets': [
            f"Событие затрагивает {main_entity}",
            "Требуется мониторинг развития",
            "Рекомендуется анализ последствий"
        ],
        'quote': "Ситуация требует внимания - система",
        'category': 'finance',
        'generated_by_ai': False
    }

def quick_why_now(importance_score):
    """Быстрое объяснение актуальности"""
    if importance_score > 0.7:
        return "🔥 Высокий приоритет"
    elif importance_score > 0.5:
        return "📈 Важное событие"
    else:
        return "📊 Информация к сведению"

def quick_timeline(article):
    """Быстрый таймлайн"""
    pub_time = article.get('published_at', datetime.now())
    return [
        f"{pub_time.strftime('%H:%M')} - Публикация",
        "Следующий час - Мониторинг реакции"
    ]

def quick_impact_level(importance_score):
    """Быстрый расчет уровня воздействия"""
    if importance_score > 0.7:
        return "высокий"
    elif importance_score > 0.5:
        return "средний"
    else:
        return "базовый"

def create_fast_news_format(raw_articles):
    """Быстрое создание формата новостей с возможностью фонового улучшения"""
    processed_news = []
    
    for article in raw_articles:
        try:
            # 
            ai_data = get_ai_enhanced_data(article['id'])
            
            if ai_data:
                #  AI-улучшенные данные
                processed_news.append(ai_data)
                continue
            
            # Быстрая обработка 
            title = article['title']
            importance_score = article.get('importance_score', 0.5)
            
            # Быстрое извлечение сущностей
            entities = quick_entity_extraction(title)
            
            # Быстрый черновик
            draft = quick_draft_generation(title, entities)
            
            processed_article = {
                'id': article['id'][:12],
                'headline': title,
                'hotness': importance_score,
                'why_now': quick_why_now(importance_score),
                'entities': entities,
                'sources': [article['url']],
                'timeline': quick_timeline(article),
                'draft': draft,
                'category': 'finance',
                'impact_level': quick_impact_level(importance_score),
                'source': article['source_name'],
                'published_at': article.get('published_at', datetime.now()).isoformat(),
                'ai_enhanced': False,
                'neural_processing': 'pending'  
            }
            
            if neural_analyzer and neural_analyzer.models_loaded:
                news_processing_queue.put((article['id'], article))
                processed_article['neural_processing'] = 'queued'
            
            processed_news.append(processed_article)
            
        except Exception as e:
            logger.error(f"Ошибка быстрой обработки статьи: {e}")
            continue
    
    return processed_news

def create_demo_data_if_needed():
    """Создает демо-данные если база пуста"""
    try:
        raw_articles = get_real_news_from_db(24, 5)
        if not raw_articles:
            logger.info("📝 Создаем демо-данные...")
            create_sample_articles()
    except Exception as e:
        logger.error(f"Ошибка проверки демо-данных: {e}")
        create_sample_articles()

def create_sample_articles():
    """Создает образцовые статьи с разными приоритетами"""
    try:
        conn = sqlite3.connect('data/news.db')
        cursor = conn.cursor()
        
        sample_articles = [
            {
                'title': '🔥 СРОЧНО: ЦБ РФ экстренно повышает ключевую ставку до 18%',
                'source': 'РБК',
                'content': 'Центральный банк принял экстренное решение о повышении ключевой ставки для стабилизации финансовой системы.',
                'url': 'https://www.rbc.ru/finance/',
                'importance': 0.95
            },
            {
                'title': 'Сбербанк объявляет о рекордной прибыли по итогам квартала',
                'source': 'РБК',
                'content': 'Крупнейший банк России показал рост прибыли на 25% благодаря увеличению кредитного портфеля.',
                'url': 'https://www.rbc.ru/finance/',
                'importance': 0.8
            },
            {
                'title': 'Рубль укрепился к доллару на фоне роста цен на нефть',
                'source': 'Ведомости', 
                'content': 'Курс рубля демонстрирует положительную динамику благодаря укреплению цен на энергоносители.',
                'url': 'https://www.vedomosti.ru/finance',
                'importance': 0.7
            },
            {
                'title': 'Мосбиржа запускает новые торговые инструменты',
                'source': 'Коммерсант',
                'content': 'Московская биржа расширяет линейку продуктов для привлечения новых инвесторов.',
                'url': 'https://www.kommersant.ru/finance',
                'importance': 0.6
            },
            {
                'title': 'Инвесторы активно покупают акции технологических компаний',
                'source': 'Финам',
                'content': 'Рынок акций показывает рост в секторе технологий на фоне оптимистичных прогнозов.',
                'url': 'https://www.finam.ru/analysis/',
                'importance': 0.5
            },
            {
                'title': 'Аналитики обсуждают перспективы рынка недвижимости',
                'source': 'РИА Новости',
                'content': 'Эксперты анализируют текущую ситуацию на рынке коммерческой недвижимости.',
                'url': 'https://ria.ru/economy/',
                'importance': 0.4
            },
            {
                'title': 'Ежеквартальный отчет по инфляции опубликован Минэкономразвития',
                'source': 'Интерфакс',
                'content': 'Министерство экономического развития опубликовало очередной отчет по инфляционным ожиданиям.',
                'url': 'https://www.interfax.ru/business/',
                'importance': 0.3
            }
        ]
        
        for article in sample_articles:
            article_id = hashlib.md5(article['title'].encode()).hexdigest()
            
            cursor.execute("SELECT id FROM raw_articles WHERE id = ?", (article_id,))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO raw_articles 
                    (id, source_name, title, url, content, published_at, collected_at, language, category, is_finance, country, importance_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article_id,
                    article['source'],
                    article['title'],
                    article['url'],
                    article['content'],
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    'ru',
                    'finance',
                    1,
                    'russia',
                    article['importance']
                ))
        
        conn.commit()
        conn.close()
        logger.info("✅ Демо-данные с разными приоритетами созданы!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания демо-данных: {e}")

def startup_sequence():
    """Последовательность запуска системы"""
    print("🚀 Запуск RADAR PRO System...")
    print("⚡ Полная функциональность + сортировка по приоритету")
    print("=" * 60)
    
    os.makedirs('data', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    initialize_components()
    
    print("✅ Система запущена и готова к работе!")
    print("🌐 Веб-интерфейс доступен по адресу: http://localhost:5000")
    print("⏰ Время запуска:", datetime.now().strftime('%Y-%m-%d %H:%M'))
    print("=" * 60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news')
def get_news():
    """API для получения новостей с поддержкой сортировки и фильтрации"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 20, type=int)
        sort_by = request.args.get('sort', 'hotness')
        priority_filter = request.args.get('priority', 'all')
        
        logger.info(f"📊 Запрос новостей: sort={sort_by}, priority={priority_filter}")
        
        raw_articles = get_real_news_from_db(
            hours=hours, 
            limit=limit, 
            sort_by=sort_by, 
            priority_filter=priority_filter
        )
        processed_news = create_fast_news_format(raw_articles)
        
        # Статистика по приоритетам
        priority_stats = {
            'high': len([n for n in processed_news if n['hotness'] > 0.7]),
            'medium': len([n for n in processed_news if 0.4 <= n['hotness'] <= 0.7]),
            'low': len([n for n in processed_news if n['hotness'] < 0.4])
        }
        
        if processed_news:
            return jsonify({
                "news": processed_news,
                "status": "success",
                "message": f"Загружено {len(processed_news)} новостей",
                "sources_count": len(set([n['source'] for n in processed_news])),
                "neural_enhanced": any(n.get('ai_enhanced', False) for n in processed_news),
                "neural_queued": any(n.get('neural_processing') == 'queued' for n in processed_news),
                "sorting": {
                    "current_sort": sort_by,
                    "current_priority": priority_filter,
                    "priority_stats": priority_stats
                }
            })
        else:
            return jsonify({
                "news": [],
                "status": "no_data", 
                "message": "Новости собираются...",
                "sources_count": 0,
                "neural_enhanced": False
            })
        
    except Exception as e:
        logger.error(f"Ошибка при получении новостей: {e}")
        return jsonify({
            "news": [],
            "status": "error",
            "message": f"Ошибка: {str(e)}"
        })

@app.route('/api/stats')
def get_stats():
    """Статистика системы"""
    try:
        raw_articles = get_real_news_from_db(24, 100)
        total_articles = len(raw_articles)
        
        priority_stats = {
            'high': len([a for a in raw_articles if a['importance_score'] > 0.7]),
            'medium': len([a for a in raw_articles if 0.4 <= a['importance_score'] <= 0.7]),
            'low': len([a for a in raw_articles if a['importance_score'] < 0.4])
        }
        
        ai_processed = 0
        try:
            conn = sqlite3.connect('data/news.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ai_article_data")
            result = cursor.fetchone()
            ai_processed = result[0] if result else 0
            conn.close()
        except:
            pass
        
        return jsonify({
            "total_articles": total_articles,
            "last_24h": total_articles,
            "sources_count": len(set([article['source_name'] for article in raw_articles])),
            "ai_processed": ai_processed,
            "neural_ready": neural_analyzer is not None and getattr(neural_analyzer, 'models_loaded', False),
            "queue_size": news_processing_queue.qsize(),
            "priority_stats": priority_stats
        })
        
    except Exception as e:
        return jsonify({
            "total_articles": 0,
            "last_24h": 0,
            "sources_count": 0,
            "ai_processed": 0,
            "neural_ready": False,
            "queue_size": 0,
            "priority_stats": {'high': 0, 'medium': 0, 'low': 0}
        })

@app.route('/api/collect-now', methods=['POST'])
def collect_now():
    """Запуск сбора новостей"""
    try:
        def collect_background():
            try:
                from data_collector import AdvancedFinanceNewsCollector
                collector = AdvancedFinanceNewsCollector()
                articles = asyncio.run(collector.collect_news_async(hours_back=24))
                logger.info(f"✅ Собрано {len(articles)} статей")
            except Exception as e:
                logger.error(f"❌ Ошибка сбора: {e}")
        
        thread = threading.Thread(target=collect_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Сбор новостей запущен! Новости появятся через 1-2 минуты."
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Ошибка: {str(e)}"
        })

@app.route('/news/<news_id>')
def news_detail(news_id):
    """Детальная страница новости"""
    try:
        # Ищем статью в базе
        conn = sqlite3.connect('data/news.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, source_name, title, url, content, published_at
            FROM raw_articles WHERE id LIKE ? || '%'
        ''', (news_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return render_template('error.html', message="Новость не найдена"), 404
        
        article = {
            'id': result[0],
            'source_name': result[1],
            'title': result[2],
            'url': result[3],
            'content': result[4] or '',
            'published_at': result[5]
        }
        
        # Улучш АИшкой
        ai_data = get_ai_enhanced_data(article['id'])
        
        if ai_data:
            news_item = ai_data
        else:
            # отображ
            processed = create_fast_news_format([article])
            if processed:
                news_item = processed[0]
            else:
                return render_template('error.html', message="Ошибка обработки новости"), 500
        
        # Используем сохраненный черновик если есть
        if news_id in news_drafts:
            news_item['draft'] = news_drafts[news_id]
            
        return render_template('news_detail.html', news=news_item)
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке деталей новости: {e}")
        return render_template('error.html', message="Ошибка загрузки"), 500

@app.route('/api/save-draft/<news_id>', methods=['POST'])
def save_draft(news_id):
    """Сохранение черновика"""
    try:
        draft_data = request.json
        news_drafts[news_id] = draft_data
        
        return jsonify({
            "status": "success",
            "message": "Черновик успешно сохранен!",
            "news_id": news_id
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Ошибка при сохранении: {str(e)}"
        }), 500

@app.route('/api/get-draft/<news_id>')
def get_draft(news_id):
    """Получение черновика"""
    if news_id in news_drafts:
        return jsonify(news_drafts[news_id])
    else:
        return jsonify({
            "title": "",
            "lead": "", 
            "bullets": [],
            "quote": ""
        })

@app.route('/api/system-status')
def system_status():
    """Статус системы"""
    return jsonify({
        "database_ready": os.path.exists('data/news.db'),
        "articles_count": len(get_real_news_from_db(24, 10)),
        "neural_ready": neural_analyzer is not None and getattr(neural_analyzer, 'models_loaded', False),
        "initial_collection": initial_collection_done,
        "collector_ready": components_ready,
        "status": "operational"
    })

@app.route('/api/neural-status')
def neural_status():
    """Статус нейросетей"""
    if not neural_analyzer:
        return jsonify({"neural_models_loaded": False})
    
    status = neural_analyzer.get_models_status()
    status['queue_size'] = news_processing_queue.qsize()
    status['processing_results'] = len(processing_results)
    return jsonify(status)

if __name__ == '__main__':
    startup_sequence()
    app.run(debug=True, port=5000, host='0.0.0.0', threaded=True)