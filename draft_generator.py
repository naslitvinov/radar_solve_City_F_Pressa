import logging
from neural_analyzer import NeuralNewsAnalyzer

logger = logging.getLogger(__name__)

class DraftGenerator:
    def __init__(self):
        self.neural_analyzer = NeuralNewsAnalyzer()
        logger.info("✅ DraftGenerator инициализирован с нейросетевым модулем")

    def generate_draft(self, article, entities):
        """Генерация черновика с использованием нейросетей"""
        try:
            # Используем нейросеть для генерации улучшенного черновика
            importance_score = self.neural_analyzer.analyze_importance(
                article.get('title', ''), 
                article.get('content', '')
            )
            
            # Извлекаем сущности с помощью NER
            ner_entities = self.neural_analyzer.extract_entities_ner(
                f"{article.get('title', '')} {article.get('content', '')}",
                language='ru'
            )
            
            # Генерируем черновик с помощью нейросети
            draft = self.neural_analyzer.generate_enhanced_draft(
                article, 
                ner_entities, 
                importance_score
            )
            
            logger.debug(f"Сгенерирован AI-черновик для: {article.get('title', '')[:50]}...")
            return draft
            
        except Exception as e:
            logger.error(f"Ошибка генерации черновика: {e}")
            return self._generate_fallback_draft(article, entities)

    def _generate_fallback_draft(self, article, entities):
        """Резервный метод генерации черновика"""
        title = article.get('title', 'Финансовая новость')
        
        return {
            'title': f"Анализ: {title}",
            'lead': "Важное событие на финансовом рынке требует внимания аналитиков и инвесторов.",
            'bullets': [
                "Событие оказывает влияние на ключевые сектора экономики",
                "Эксперты оценивают возможные последствия для рынка", 
                "Рекомендуется мониторинг развития ситуации в ближайшее время"
            ],
            'quote': "Текущая динамика требует внимательного анализа - финансовый эксперт",
            'category': 'finance',
            'generated_by_ai': False
        }