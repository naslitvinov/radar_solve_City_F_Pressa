import requests
from bs4 import BeautifulSoup
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_selectors():
    """Тестирование и поиск правильных селекторов для источников новостей"""
    
    test_sources = [
        {
            "name": "РБК Финансы",
            "url": "https://www.rbc.ru/finances/",
            "possible_selectors": [
                "a.news-feed__item",
                "div.news-feed__item", 
                "span.news-feed__item__title",
                "a.main__feed__link"
            ]
        },
        {
            "name": "Коммерсант Финансы",
            "url": "https://www.kommersant.ru/finance",
            "possible_selectors": [
                "a.uho__link",
                "div.uho",
                "h2.vam__head",
                "article"
            ]
        },
        {
            "name": "Интерфакс Финансы", 
            "url": "https://www.interfax.ru/business/",
            "possible_selectors": [
                "div.newsTimeline__item",
                "a.newsTimeline__item__title",
                "div.an",
                "a.an__text"
            ]
        },
        {
            "name": "Reuters Business",
            "url": "https://www.reuters.com/business/",
            "possible_selectors": [
                "a[data-testid*='Heading']",
                "div[data-testid*='story']",
                "article",
                "div.story-card"
            ]
        },
        {
            "name": "Банки.ру Новости",
            "url": "https://www.banki.ru/news/",
            "possible_selectors": [
                "a.text-color-black", 
                "div.news-item",
                "article.news-list-item"
            ]
        }
    ]

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })

    results = {}

    for source in test_sources:
        print(f"\n{'='*60}")
        print(f"🔍 ТЕСТИРУЕМ: {source['name']}")
        print(f"🌐 URL: {source['url']}")
        print(f"{'='*60}")
        
        results[source['name']] = {
            'url': source['url'],
            'selectors': {}
        }

        try:
            response = session.get(source['url'], timeout=15, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Тестируем каждый селектор
            for selector in source['possible_selectors']:
                elements = soup.select(selector)
                print(f"\n📌 Селектор: '{selector}'")
                print(f"   Найдено элементов: {len(elements)}")
                
                results[source['name']]['selectors'][selector] = len(elements)
                
                if elements:
                    # Показываем информацию о первых 2 элементах
                    for i, elem in enumerate(elements[:2]):
                        text = elem.get_text().strip().replace('\n', ' ')[:80]
                        href = elem.get('href', '') if hasattr(elem, 'get') else ''
                        
                        print(f"   {i+1}. Текст: {text}...")
                        if href:
                            # Преобразуем относительные ссылки в абсолютные
                            if href.startswith('//'):
                                full_url = f"https:{href}"
                            elif href.startswith('/'):
                                base_url = '/'.join(source['url'].split('/')[:3])
                                full_url = base_url + href
                            else:
                                full_url = href
                            print(f"      🔗 Ссылка: {full_url}")

            # Дополнительно: поиск всех ссылок с текстом (первые 5)
            print(f"\n📎 Все ссылки на странице (первые 5):")
            all_links = soup.find_all('a', href=True, string=True)
            link_count = 0
            for link in all_links:
                text = link.get_text().strip()
                href = link.get('href')
                if text and len(text) > 15 and not any(skip in href for skip in ['javascript:', '#', 'mailto:']):
                    print(f"   🔗 {text[:50]}... -> {href}")
                    link_count += 1
                    if link_count >= 5:
                        break

        except Exception as e:
            print(f"❌ Ошибка при тестировании {source['name']}: {e}")
            results[source['name']]['error'] = str(e)
            continue

    # Сохраняем результаты в JSON файл
    with open('data/selector_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены в data/selector_test_results.json")
    
    # Рекомендации по лучшим селекторам
    print(f"\n🎯 РЕКОМЕНДАЦИИ ПО СЕЛЕКТОРАМ:")
    for source_name, data in results.items():
        if 'selectors' in data:
            best_selector = max(data['selectors'].items(), key=lambda x: x[1])
            if best_selector[1] > 0:
                print(f"   {source_name}: '{best_selector[0]}' ({best_selector[1]} элементов)")

def update_sources_config():
    """Обновление конфигурации sources.json на основе результатов тестирования"""
    try:
        with open('data/selector_test_results.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        with open('config/sources.json', 'r', encoding='utf-8') as f:
            sources_config = json.load(f)
        
        updated = False
        
        for source in sources_config.get('html_sources', []):
            source_name = source['name']
            if source_name in results and 'selectors' in results[source_name]:
                # Находим селектор с максимальным количеством элементов
                selectors = results[source_name]['selectors']
                if selectors:
                    best_selector = max(selectors.items(), key=lambda x: x[1])
                    if best_selector[1] > 0:
                        # Обновляем селектор статьи
                        source['selectors']['article'] = best_selector[0]
                        print(f"✅ Обновлен {source_name}: article -> '{best_selector[0]}'")
                        updated = True
        
        if updated:
            with open('config/sources.json', 'w', encoding='utf-8') as f:
                json.dump(sources_config, f, ensure_ascii=False, indent=2)
            print("💾 Конфигурация sources.json обновлена!")
        else:
            print("ℹ️ Изменений не требуется")
            
    except FileNotFoundError:
        print("❌ Файл с результатами тестирования не найден. Сначала запустите test_selectors()")

if __name__ == "__main__":
    print("🎯 ИНСТРУМЕНТ ТЕСТИРОВАНИЯ СЕЛЕКТОРОВ НОВОСТЕЙ")
    print("=" * 60)
    
    while True:
        print("\nВыберите действие:")
        print("1. Тестировать селекторы источников")
        print("2. Обновить конфигурацию sources.json")
        print("3. Выход")
        
        choice = input("\nВаш выбор (1/2/3): ").strip()
        
        if choice == '1':
            test_selectors()
        elif choice == '2':
            update_sources_config()
        elif choice == '3':
            print("👋 Выход из программы")
            break
        else:
            print("❌ Неверный выбор, попробуйте снова")