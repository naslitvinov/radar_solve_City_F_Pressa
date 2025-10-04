import logging
from neural_analyzer import NeuralNewsAnalyzer

logger = logging.getLogger(__name__)

class HotnessAnalyzer:
    def __init__(self):
        self.neural_analyzer = NeuralNewsAnalyzer()
        logger.info("✅ HotnessAnalyzer инициализирован с нейросетевым модулем")

    def analyze_article(self, article):
        """Анализ статьи с использованием нейросетей"""
        try:
            title = article.get('title', '')
            content = article.get('content', '') or ''
            
            # Используем НС для оценки важности
            importance_score = self.neural_analyzer.analyze_importance(title, content)
            
            #  корректировки 
            final_score = self._adjust_with_metadata(importance_score, article)
            
            logger.debug(f"Оценка важности для '{title[:50]}...': {final_score:.3f}")
            return final_score
            
        except Exception as e:
            logger.error(f"Ошибка анализа статьи: {e}")
            return self._fallback_analysis(article)

    def _adjust_with_metadata(self, base_score, article):
        """Корректировка оценки на основе мета-данных"""
        score = base_score
        
        # Корректировка по источнику
        source_score = self._calculate_source_score(article.get('source_name', ''))
        score = score * 0.7 + source_score * 0.3
        
        # Корректировка по времени
        time_score = self._calculate_time_score(article.get('published_at'))
        score = score * 0.8 + time_score * 0.2
        
        return min(max(score, 0.1), 0.99)

    def _calculate_source_score(self, source_name):
        """Вес источника"""
        source_weights = {
            'РБК': 0.9, 'Reuters': 0.95, 'Интерфакс': 0.85,
            'Коммерсант': 0.88, 'ТАСС': 0.87, 'Ведомости': 0.82,
            'Банки.ру': 0.75, 'Финам': 0.7, 'Инвестиции': 0.65,
            'РИА Новости': 0.8, 'Lenta.ru': 0.7, 'Forbes': 0.85,
            'Bloomberg': 0.95
        }
        
        for source, weight in source_weights.items():
            if source in source_name:
                return weight
        return 0.5

    def _calculate_time_score(self, published_at):
        """Оценка актуальности по времени"""
        from datetime import datetime, timedelta
        
        if not published_at:
            return 0.5
            
        try:
            if isinstance(published_at, str):
                from datetime import datetime
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            
            now = datetime.now()
            hours_diff = (now - published_at).total_seconds() / 3600
            
            if hours_diff < 1: return 1.0
            elif hours_diff < 3: return 0.8
            elif hours_diff < 6: return 0.6
            elif hours_diff < 12: return 0.4
            elif hours_diff < 24: return 0.3
            else: return 0.2
            
        except Exception:
            return 0.5

    def _fallback_analysis(self, article):
        """Резервный анализ при ошибке"""
        text = f"{article.get('title', '')} {article.get('content', '')}".lower()
        
        score = 0.3
        important_terms = ['срочн', 'экстрен', 'кризис', 'важн', 'значительн']
        
        for term in important_terms:
            if term in text:
                score += 0.1
                
        return min(max(score, 0.1), 0.8)
