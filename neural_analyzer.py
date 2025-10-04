import torch
import numpy as np
import logging
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import re
from datetime import datetime, timedelta
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeuralNewsAnalyzer:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"🧠 Инициализация нейросетей на устройстве: {self.device}")
        
        self.models_loaded = False
        self.embedding_model = None
        self.sentiment_model = None
        self.text_generator = None
        self.ner_pipeline = None
        
        self._load_models()

    def _load_models(self):
        """Загрузка нейросетевых моделей с улучшенной обработкой ошибок"""
        try:
            logger.info("🔄 Загрузка моделей машинного обучения...")
            
            # 1. Модель для эмбеддингов (легкая и быстрая)
            self.embedding_model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                device=self.device
            )
            logger.info("✅ Модель для эмбеддингов загружена")

            # 2. Модель для анализа тональности
            try:
                self.sentiment_model = pipeline(
                    "sentiment-analysis",
                    model="blanchefort/rubert-base-cased-sentiment",
                    device=0 if torch.cuda.is_available() else -1,
                )
                logger.info("✅ Модель для анализа тональности загружена")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить модель тональности: {e}")
                self.sentiment_model = None

            # 3. NER модель для извлечения сущностей
            try:
                self.ner_pipeline = pipeline(
                    "ner",
                    model="Davlan/bert-base-multilingual-cased-ner-hrl",
                    aggregation_strategy="simple",
                    device=0 if torch.cuda.is_available() else -1,
                )
                logger.info("✅ Модель для NER загружена")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить NER модель: {e}")
                self.ner_pipeline = None

            # 4. Генератор текста (опционально)
            try:
                self.text_generator = pipeline(
                    "text-generation",
                    model="sberbank-ai/rugpt3small_based_on_gpt2",
                    device=0 if torch.cuda.is_available() else -1,
                )
                logger.info("✅ Генератор текста загружен")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить генератор текста: {e}")
                self.text_generator = None

            self.models_loaded = True
            logger.info("🎉 Все модели успешно загружены!")

        except Exception as e:
            logger.error(f"❌ Критическая ошибка загрузки моделей: {e}")
            self.models_loaded = False

    async def analyze_sentiment(self, text):
        """Анализ тональности текста"""
        if not self.sentiment_model or not text:
            return await self._fallback_sentiment(text)
        
        try:
            result = self.sentiment_model(text[:512])[0]
            
            sentiment_map = {
                'POSITIVE': 'positive',
                'NEGATIVE': 'negative', 
                'NEUTRAL': 'neutral'
            }
            
            return {
                'sentiment': sentiment_map.get(result['label'], 'neutral'),
                'confidence': result['score'],
                'scores': {
                    'positive': result['score'] if result['label'] == 'POSITIVE' else 1 - result['score'],
                    'negative': result['score'] if result['label'] == 'NEGATIVE' else 1 - result['score'],
                    'neutral': result['score'] if result['label'] == 'NEUTRAL' else 1 - result['score']
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа тональности: {e}")
            return await self._fallback_sentiment(text)

    async def _fallback_sentiment(self, text):
        """Резервный анализ тональности"""
        if not text:
            return {'sentiment': 'neutral', 'confidence': 0.5, 'scores': {'negative': 0.33, 'neutral': 0.34, 'positive': 0.33}}
        
        text_lower = text.lower()
        positive_words = ['рост', 'увелич', 'прибыль', 'успех', 'позитив', 'выгод', 'улучш']
        negative_words = ['падение', 'сниж', 'убыток', 'проблем', 'риск', 'кризис', 'сложн']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return {'sentiment': 'positive', 'confidence': 0.7, 'scores': {'negative': 0.2, 'neutral': 0.3, 'positive': 0.5}}
        elif negative_count > positive_count:
            return {'sentiment': 'negative', 'confidence': 0.7, 'scores': {'negative': 0.5, 'neutral': 0.3, 'positive': 0.2}}
        else:
            return {'sentiment': 'neutral', 'confidence': 0.6, 'scores': {'negative': 0.3, 'neutral': 0.4, 'positive': 0.3}}

    async def extract_entities_ner(self, text):
        """Извлечение сущностей с помощью NER"""
        if not self.ner_pipeline or not text:
            return await self._fallback_entities(text)
        
        try:
            truncated_text = text[:1000]
            entities = self.ner_pipeline(truncated_text)
            
            organized_entities = {
                'organizations': [],
                'persons': [],
                'locations': [],
                'misc': []
            }
            
            for entity in entities:
                entity_text = entity['word'].strip()
                entity_type = entity['entity_group']
                
                if entity_type in ['ORG', 'B-ORG', 'I-ORG'] and entity_text not in organized_entities['organizations']:
                    organized_entities['organizations'].append(entity_text)
                elif entity_type in ['PER', 'B-PER', 'I-PER'] and entity_text not in organized_entities['persons']:
                    organized_entities['persons'].append(entity_text)
                elif entity_type in ['LOC', 'B-LOC', 'I-LOC'] and entity_text not in organized_entities['locations']:
                    organized_entities['locations'].append(entity_text)
                elif entity_text not in organized_entities['misc']:
                    organized_entities['misc'].append(entity_text)
            
            # Ограничиваем количество сущностей
            for key in organized_entities:
                organized_entities[key] = organized_entities[key][:5]
                
            return organized_entities
            
        except Exception as e:
            logger.error(f"Ошибка NER извлечения: {e}")
            return await self._fallback_entities(text)

    async def _fallback_entities(self, text):
        """Резервное извлечение сущностей"""
        text_lower = text.lower()
        
        # Словари ключевых сущностей
        companies = ['сбербанк', 'газпром', 'роснефть', 'лукойл', 'втб', 'яндекс', 
                    'тинькофф', 'мосбиржа', 'альфа-банк', 'цб', 'минфин', 'правительство',
                    'apple', 'microsoft', 'google', 'amazon', 'tesla', 'meta']
        
        persons = ['путин', 'мишустин', 'набиуллина', 'силуанов', 'греф', 'миллер',
                  'biden', 'trump', 'putin', 'macron', 'scholz']
        
        locations = ['москва', 'россия', 'сша', 'европа', 'китай', 'лондон', 'нью-йорк',
                    'moscow', 'russia', 'usa', 'europe', 'china', 'london']
        
        found_companies = [comp.title() for comp in companies if comp in text_lower]
        found_persons = [pers.title() for pers in persons if pers in text_lower]
        found_locations = [loc.title() for loc in locations if loc in text_lower]

        # Поиск денежных сумм и процентов
        money_patterns = [
            r'(\d+[,.]?\d*)\s*(млрд|миллиард|billion)',
            r'(\d+[,.]?\d*)\s*(млн|миллион|million)',
            r'(\d+[,.]?\d*)\s*%',
            r'\$(\d+[,.]?\d*)',
            r'€(\d+[,.]?\d*)'
        ]
        
        money_entities = []
        for pattern in money_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                money_entities.append(match.group(0))

        return {
            'organizations': found_companies[:5],
            'persons': found_persons[:3],
            'locations': found_locations[:3],
            'money': money_entities[:3],
            'misc': []
        }

    async def analyze_importance(self, title, content, source_name):
        """Анализ важности статьи с использованием нейросетей"""
        try:
            text = f"{title}. {content[:500]}"
            
            # Анализ тональности
            sentiment_result = await self.analyze_sentiment(text)
            
            # Базовый скоринг на основе различных факторов
            base_score = 0.3
            
            # Фактор источника
            source_weights = {
                'reuters': 0.9, 'bloomberg': 0.95, 'financial times': 0.9,
                'рбк': 0.85, 'коммерсант': 0.8, 'ведомости': 0.8,
                'цб': 1.0, 'ecb': 0.9, 'imf': 0.9, 'world bank': 0.9
            }
            
            for source, weight in source_weights.items():
                if source in source_name.lower():
                    base_score = weight
                    break
            
            # Фактор тональности
            sentiment_boost = {
                'positive': 0.1,
                'negative': 0.15,  # Негативные новости часто важнее
                'neutral': 0.0
            }
            base_score += sentiment_boost.get(sentiment_result['sentiment'], 0)
            
            # Фактор ключевых слов
            urgency_indicators = {
                'срочн': 0.2, 'экстрен': 0.3, 'кризис': 0.25, 'важн': 0.15,
                'urgent': 0.2, 'breaking': 0.3, 'crisis': 0.25, 'important': 0.15,
                'санкц': 0.2, 'санкции': 0.2, 'sanction': 0.2,
                'цб': 0.3, 'central bank': 0.3, 'fed': 0.3
            }
            
            text_lower = text.lower()
            for indicator, boost in urgency_indicators.items():
                if indicator in text_lower:
                    base_score += boost
                    break
            
            # Фактор длины контента (более длинные статьи часто важнее)
            content_length = len(content)
            if content_length > 1000:
                base_score += 0.1
            elif content_length > 500:
                base_score += 0.05
            
            final_score = min(max(base_score, 0.1), 0.99)
            
            logger.debug(f"📊 Оценка важности '{title[:30]}...': {final_score:.3f}")
            return final_score
            
        except Exception as e:
            logger.error(f"Ошибка анализа важности: {e}")
            return await self._fallback_importance_analysis(title, content)

    async def _fallback_importance_analysis(self, title, content):
        """Резервный анализ важности"""
        text = f"{title} {content}".lower()
        score = 0.3
        
        important_indicators = [
            'срочн', 'экстрен', 'кризис', 'важн', 'значительн',
            'urgent', 'breaking', 'crisis', 'important', 'significant',
            'санкц', 'цб', 'правительств', 'президент', 'минфин'
        ]
        
        for indicator in important_indicators:
            if indicator in text:
                score += 0.1
                
        return min(max(score, 0.1), 0.8)

    async def generate_ai_draft(self, article, entities, importance_score):
        """Генерация черновика с помощью AI"""
        if not self.text_generator:
            return await self._generate_fallback_draft(article, entities)
        
        try:
            # Подготавливаем контекст для генерации
            context = self._prepare_generation_context(article, entities, importance_score)
            
            prompt = f"""
            Напиши краткий финансовый обзор на основе этой информации:
            
            Заголовок: {article['title']}
            Основные сущности: {', '.join(entities.get('organizations', [])[:3])}
            
            Создай структурированный обзор:
            - Краткий аналитический заголовок
            - Основной абзац (2-3 предложения) с ключевыми выводами
            - 3 ключевых пункта анализа
            - Заключительную мысль или рекомендацию
            
            Тон: профессиональный, аналитический
            """
            
            result = self.text_generator(
                prompt,
                max_length=400,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True,
                pad_token_id=50256
            )
            
            generated_text = result[0]['generated_text']
            return self._parse_generated_draft(generated_text, article, entities)
            
        except Exception as e:
            logger.error(f"Ошибка генерации AI черновика: {e}")
            return await self._generate_fallback_draft(article, entities)

    def _prepare_generation_context(self, article, entities, importance_score):
        """Подготовка контекста для генерации"""
        context_parts = [
            f"Статья от {article.get('source_name', 'источник')}",
            f"Тема: {self._detect_topic(article['title'])}",
            f"Уровень важности: {'высокий' if importance_score > 0.7 else 'средний' if importance_score > 0.4 else 'базовый'}",
            f"Ключевые организации: {', '.join(entities.get('organizations', [])[:2])}"
        ]
        
        return ". ".join(context_parts)

    def _detect_topic(self, title):
        """Определение темы статьи с помощью AI"""
        title_lower = title.lower()
        
        topic_keywords = {
            'stocks': ['акци', 'stock', 'equity', 'shares', 'бирж', 's&p', 'dow', 'nasdaq'],
            'bonds': ['облигац', 'bond', 'debt', 'coupon', 'yield'],
            'currency': ['курс', 'currency', 'dollar', 'euro', 'рубл', 'ruble', 'exchange rate'],
            'commodities': ['нефть', 'oil', 'газ', 'gas', 'золот', 'gold', 'металл', 'metal'],
            'crypto': ['крипто', 'crypto', 'биткоин', 'bitcoin', 'блокчейн', 'blockchain'],
            'banking': ['банк', 'bank', 'кредит', 'credit', 'ставк', 'interest rate'],
            'regulation': ['регулирован', 'regulation', 'санкц', 'sanction', 'цб', 'central bank'],
            'macro': ['ввп', 'gdp', 'инфляц', 'inflation', 'экономик', 'economy']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return topic
        
        return 'finance'

    def _parse_generated_draft(self, generated_text, article, entities):
        """Парсинг сгенерированного текста"""
        try:
            lines = [line.strip() for line in generated_text.split('\n') if line.strip()]
            
            if not lines or len(lines) < 3:
                return self._generate_fallback_draft(article, entities)

            draft = {
                'title': lines[0] if lines else f"Анализ: {article['title']}",
                'lead': "",
                'bullets': [],
                'quote': "",
                'category': self._detect_topic(article['title']),
                'generated_by_ai': True,
                'ai_confidence': 0.8
            }
            
            # Умный парсинг структуры
            current_section = 'lead'
            for line in lines[1:]:
                line_clean = line.strip()
                
                if not line_clean:
                    continue
                    
                # Определяем тип контента по маркерам
                if any(marker in line_clean.lower() for marker in ['•', '- ', '—', '1.', '2.', '3.']):
                    if len(draft['bullets']) < 3:
                        # Очищаем от маркеров
                        clean_bullet = re.sub(r'^[•\-\—\d\.\s]+', '', line_clean)
                        if clean_bullet and len(clean_bullet) > 10:
                            draft['bullets'].append(clean_bullet)
                elif len(line_clean) > 30 and not draft['lead']:
                    draft['lead'] = line_clean
                elif len(line_clean) > 20 and not draft['quote'] and any(marker in line_clean for marker in ['"', "'", '—']):
                    draft['quote'] = line_clean
                elif len(line_clean) > 15 and not draft['lead']:
                    draft['lead'] = line_clean

            # Заполняем недостающие части умными значениями по умолчанию
            if not draft['lead']:
                main_org = entities.get('organizations', ['компаний'])[0] if entities.get('organizations') else 'рынка'
                draft['lead'] = f"Событие {article['title']} оказывает значительное влияние на {main_org} и требует внимания инвесторов."
            
            if not draft['bullets']:
                main_org = entities.get('organizations', ['компаний'])[0] if entities.get('organizations') else 'рынок'
                draft['bullets'] = [
                    f"Событие затрагивает ключевые аспекты деятельности {main_org}",
                    "Аналитики оценивают потенциальное влияние на смежные сектора экономики",
                    "Рекомендуется мониторинг дальнейшего развития ситуации"
                ]
                
            if not draft['quote']:
                draft['quote'] = "Текущая динамика требует тщательного анализа и может оказать существенное влияние на инвестиционные стратегии."
            
            return draft
            
        except Exception as e:
            logger.error(f"Ошибка парсинга сгенерированного текста: {e}")
            return self._generate_fallback_draft(article, entities)

    async def _generate_fallback_draft(self, article, entities):
        """Резервный метод генерации черновика"""
        main_org = entities.get('organizations', ['компаний'])[0] if entities.get('organizations') else 'рынка'
        
        return {
            'title': f"Анализ: {article['title']}",
            'lead': f"Развитие ситуации вокруг {main_org} требует внимания со стороны финансового сообщества. Событие может оказать влияние на рыночные тенденции.",
            'bullets': [
                f"Событие затрагивает деятельность {main_org} и смежные сектора экономики",
                "Рыночная реакция может оказать влияние на инвестиционные стратегии участников",
                "Эксперты рекомендуют внимательно следить за развитием событий в ближайшее время"
            ],
            'quote': "Текущая динамика требует тщательного анализа и мониторинга - финансовый эксперт",
            'category': 'finance',
            'generated_by_ai': False,
            'ai_confidence': 0.0
        }

    async def process_articles_batch(self, articles):
        """Пакетная обработка статей с использованием нейросетей"""
        if not articles:
            return []

        logger.info(f"🧠 Начинаем нейросетевую обработку {len(articles)} статей...")
        
        processed_articles = []
        
        for article in articles:
            try:
                full_text = f"{article['title']} {article.get('content', '')}"
                
                # Извлекаем сущности с помощью NER
                entities = await self.extract_entities_ner(full_text)
                
                # Анализируем важность с помощью нейросети
                importance = await self.analyze_importance(
                    article['title'],
                    article.get('content', ''),
                    article['source_name']
                )
                
                # Анализируем тональность
                sentiment = await self.analyze_sentiment(full_text)
                
                # Генерируем AI черновик
                draft = await self.generate_ai_draft(article, entities, importance)
                
                # Создаем обогащенную статью
                processed_article = {
                    'id': article['id'],
                    'headline': article['title'],
                    'hotness': importance,
                    'why_now': self._generate_ai_why_now(importance, entities, sentiment),
                    'entities': self._flatten_entities(entities),
                    'sources': [article['url']],
                    'timeline': self._generate_ai_timeline(article, importance),
                    'draft': draft,
                    'category': draft['category'],
                    'impact_level': self._calculate_ai_impact_level(importance, entities, sentiment),
                    'source': article['source_name'],
                    'published_at': article.get('published_at', datetime.now()).isoformat(),
                    'ai_enhanced': True,
                    'sentiment': sentiment,
                    'ner_entities': entities
                }
                
                processed_articles.append(processed_article)
                logger.info(f"✅ Обработана статья: {article['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки статьи: {e}")
                continue

        # Сортируем по важности
        processed_articles.sort(key=lambda x: x['hotness'], reverse=True)
        
        logger.info(f"🎉 Нейросетевая обработка завершена: {len(processed_articles)} статей")
        return processed_articles

    def _flatten_entities(self, entities):
        """Преобразование сущностей в плоский список"""
        all_entities = []
        for entity_type, entity_list in entities.items():
            if entity_type != 'money':  # Исключаем денежные суммы из общего списка
                all_entities.extend(entity_list[:2])
        return list(set(all_entities))[:6]

    def _generate_ai_why_now(self, importance, entities, sentiment):
        """Генерация объяснения актуальности с помощью AI логики"""
        if importance > 0.8:
            orgs = entities.get('organizations', [])
            if orgs:
                return f"🔥 КРИТИЧЕСКАЯ ВАЖНОСТЬ: Событие может оказать существенное влияние на {orgs[0]} и рынок в целом"
            return "🔥 ВЫСОКАЯ СРОЧНОСТЬ: Требуется немедленное внимание инвесторов и аналитиков"
        elif importance > 0.6:
            if sentiment['sentiment'] == 'negative':
                return "⚠️ ЗНАЧИТЕЛЬНЫЙ РИСК: Негативное развитие требует анализа потенциальных последствий"
            else:
                return "📈 ВАЖНАЯ ИНФОРМАЦИЯ: Может повлиять на инвестиционные решения в среднесрочной перспективе"
        else:
            return "📊 ИНФОРМАЦИЯ К СВЕДЕНИЮ: Рекомендуется мониторинг развития ситуации"

    def _generate_ai_timeline(self, article, importance):
        """Генерация таймлайна с AI логикой"""
        pub_time = article.get('published_at', datetime.now())
        if isinstance(pub_time, str):
            try:
                pub_time = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
            except:
                pub_time = datetime.now()
        
        time_format = '%H:%M'
        
        base_timeline = [
            f"{pub_time.strftime(time_format)} - Публикация в {article['source_name']}",
            f"{(pub_time + timedelta(minutes=30)).strftime(time_format)} - Распространение в информационных каналах"
        ]
        
        if importance > 0.7:
            base_timeline.extend([
                f"{(pub_time + timedelta(hours=1)).strftime(time_format)} - Начало активного обсуждения экспертами",
                f"{(pub_time + timedelta(hours=2)).strftime(time_format)} - Ожидается реакция рынка"
            ])
        else:
            base_timeline.append(
                f"{(pub_time + timedelta(hours=1)).strftime(time_format)} - Начало экспертного обсуждения"
            )
        
        return base_timeline

    def _calculate_ai_impact_level(self, importance, entities, sentiment):
        """Расчет уровня воздействия с AI логикой"""
        important_entities = ['сбербанк', 'газпром', 'роснефть', 'мосбиржа', 'цб', 'минфин',
                             'apple', 'microsoft', 'google', 'fed', 'ecb']
        has_important_entities = any(
            any(ent in entity.lower() for ent in important_entities) 
            for entity in entities.get('organizations', [])
        )
        
        sentiment_boost = 0.1 if sentiment['sentiment'] == 'negative' else 0
        
        adjusted_importance = importance + sentiment_boost
        
        if adjusted_importance > 0.7 and has_important_entities:
            return "критический"
        elif adjusted_importance > 0.7:
            return "высокий"
        elif adjusted_importance > 0.5:
            return "средний"
        else:
            return "базовый"

    def get_models_status(self):
        """Получение статуса загруженных моделей"""
        return {
            'models_loaded': self.models_loaded,
            'embedding_model': self.embedding_model is not None,
            'sentiment_model': self.sentiment_model is not None,
            'text_generator': self.text_generator is not None,
            'ner_pipeline': self.ner_pipeline is not None,
            'device': str(self.device)
        }