
window.currentSort = 'hotness';
window.currentPriority = 'all';

function initializeSorting() {
    const sortSelect = document.getElementById('sort-select');
    const prioritySelect = document.getElementById('priority-select');
    
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            window.currentSort = this.value;
            loadNews();
        });
    }
    
    if (prioritySelect) {
        prioritySelect.addEventListener('change', function() {
            window.currentPriority = this.value;
            loadNews();
        });
    }
}

async function loadNews() {
    showLoading(true);
    
    try {
        const url = `/api/news?hours=24&limit=20&sort=${window.currentSort}&priority=${window.currentPriority}`;
        
        console.log('Loading news with sorting:', { 
            sort: window.currentSort, 
            priority: window.currentPriority 
        });
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('News response with sorting:', data);
        
        if (data.status === 'error') {
            showError(data.message || 'Ошибка загрузки новостей');
        } else if (data.status === 'no_data') {
            showNotification(data.message, 'info');
        }
        
        window.currentNewsData = data.news || [];
        displayNews(data.news || []);
        updateStats(data.news || []);
        updateLastUpdated();
        
        
        updateSortingInfo(data.sorting);
        
    } catch (error) {
        console.error('Error loading news:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        showLoading(false);
    }
}

function updateSortingInfo(sortingInfo) {
    const sortingInfoElement = document.getElementById('sorting-info');
    if (!sortingInfoElement || !sortingInfo) return;
    
    const priorityStats = sortingInfo.priority_stats || {};
    
    sortingInfoElement.innerHTML = `
        <div class="sorting-stats">
            <span>📊 Сортировка: ${getSortLabel(sortingInfo.current_sort)}</span>
            <span>🎯 Приоритет: ${getPriorityLabel(sortingInfo.current_priority)}</span>
            <span class="priority-badges">
                <span class="priority-badge high">🔥 ${priorityStats.high || 0}</span>
                <span class="priority-badge medium">📈 ${priorityStats.medium || 0}</span>
                <span class="priority-badge low">📊 ${priorityStats.low || 0}</span>
            </span>
        </div>
    `;
}

function getSortLabel(sort) {
    const labels = {
        'hotness': 'По важности',
        'date_new': 'По дате (новые)',
        'date_old': 'По дате (старые)',
        'source': 'По источнику'
    };
    return labels[sort] || sort;
}

function getPriorityLabel(priority) {
    const labels = {
        'all': 'Все',
        'high': 'Высокий',
        'medium': 'Средний',
        'low': 'Низкий'
    };
    return labels[priority] || priority;
}

function displayNews(newsArray) {
    const container = document.getElementById('news-container');
    
    if (!newsArray || newsArray.length === 0) {
        container.innerHTML = `
            <div class="no-news">
                <h3>📭 Новостей пока нет</h3>
                <p>Попробуйте изменить фильтры или запустить сбор новостей.</p>
                <div class="no-news-actions">
                    <button onclick="collectNow()" class="btn btn-primary">🚀 Запустить сбор</button>
                    <button onclick="loadNews()" class="btn btn-secondary">🔄 Обновить</button>
                </div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = newsArray.map(news => `
        <div class="news-card priority-${getPriorityClass(news.hotness)}">
            <div class="news-header">
                <span class="category-tag">${news.category}</span>
                <span class="impact-badge impact-${news.impact_level}">
                    ${getPriorityIcon(news.hotness)} ${news.impact_level} приоритет
                </span>
            </div>
            <div class="news-source">📰 ${news.source}</div>
            <div class="hotness-indicator">
                <div class="hotness-bar">
                    <div class="hotness-fill" style="width: ${Math.round(news.hotness * 100)}%"></div>
                </div>
                <div class="hotness-score">${news.hotness.toFixed(2)}</div>
            </div>
            <h2>${news.headline}</h2>
            <p class="why-now">${news.why_now}</p>
            <div class="entities-preview">
                ${(news.entities || []).slice(0, 4).map(entity => `
                    <span class="entity-tag">${entity}</span>
                `).join('')}
                ${(news.entities || []).length > 4 ? `<span class="entity-more">+${(news.entities || []).length - 4}</span>` : ''}
            </div>
            <div class="news-actions">
                <a href="/news/${news.id}" class="btn btn-secondary">Анализ и черновик →</a>
            </div>
        </div>
    `).join('');
}

function getPriorityClass(hotness) {
    if (hotness > 0.7) return 'high';
    if (hotness > 0.4) return 'medium';
    return 'low';
}

function getPriorityIcon(hotness) {
    if (hotness > 0.7) return '🔥';
    if (hotness > 0.4) return '📈';
    return '📊';
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing RADAR System with sorting...');
    
    addDynamicStyles();
    
    if (document.getElementById('refresh-btn')) {
        initializeMainPage();
        initializeSorting(); 
    }
});
console.log("RADAR System initialized successfully!");

window.currentNewsData = [];
window.updateCount = 0;

function initializeMainPage() {
    const refreshBtn = document.getElementById('refresh-btn');
    const collectBtn = document.getElementById('collect-now-btn');
    
    if (refreshBtn) {
        checkSystemStatus();
        loadNews();
        loadSystemStats();
        refreshBtn.addEventListener('click', refreshNews);
        
        startAutoStatusCheck();
    }
    
    if (collectBtn) {
        collectBtn.addEventListener('click', collectNow);
    }
}

async function checkSystemStatus() {
    try {
        const response = await fetch('/api/system-status');
        const status = await response.json();
        
        updateSystemStatus(status);
        
    } catch (error) {
        console.error('Error checking system status:', error);
        updateSystemStatus({ status: 'error' });
    }
}

function updateSystemStatus(status) {
    const statusElement = document.getElementById('system-status');
    const statusText = document.getElementById('status-text');
    
    if (!statusElement || !statusText) return;
    
    switch (status.status) {
        case 'operational':
            statusElement.className = 'status-indicator active';
            statusText.textContent = '✓ Система активна';
            break;
        case 'collecting':
            statusElement.className = 'status-indicator collecting';
            statusText.textContent = '🔄 Собираем новости...';
            break;
        case 'initializing':
            statusElement.className = 'status-indicator initializing';
            statusText.textContent = '⚙️ Инициализация...';
            break;
        case 'error':
            statusElement.className = 'status-indicator error';
            statusText.textContent = '❌ Ошибка системы';
            break;
        default:
            statusElement.className = 'status-indicator';
            statusText.textContent = '⚡ Загрузка...';
    }
}

async function loadNews() {
    showLoading(true);
    
    try {
        const priorityFilter = document.getElementById('priority-filter');
        const priorityValue = priorityFilter ? priorityFilter.value : 'all';
        const url = priorityValue === 'all' ? '/api/news?hours=24&limit=12' : `/api/news?hours=24&limit=12&priority=${priorityValue}`;
        
        console.log('Loading news from:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('News response:', data);
        
        if (data.status === 'error') {
            showError(data.message || 'Ошибка загрузки новостей');
        } else if (data.status === 'no_data') {
            showNotification(data.message, 'info');
        }
        
        window.currentNewsData = data.news || [];
        displayNews(data.news || []);
        updateStats(data.news || []);
        updateLastUpdated();
        
    } catch (error) {
        console.error('Error loading news:', error);
        showError('Ошибка подключения к серверу. Проверьте, запущен ли сервер на порту 5000.');
    } finally {
        showLoading(false);
    }
}

async function loadSystemStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (!data.error) {
            document.getElementById('total-articles').textContent = data.total_articles || 0;
            document.getElementById('last-24h').textContent = data.last_24h || 0;
            document.getElementById('sources-count').textContent = data.total_sources || 0;
            
            document.getElementById('last-update-count').textContent = data.last_24h || 0;
            
            if (data.initial_collection !== undefined) {
                const collectionStatus = document.getElementById('collection-status');
                if (collectionStatus) {
                    collectionStatus.textContent = data.initial_collection ? 
                        '✅ Автосбор завершен' : '🔄 Идет автосбор...';
                }
            }
        }
    } catch (error) {
        console.error('Error loading system stats:', error);
    }
}

function displayNews(newsArray) {
    const container = document.getElementById('news-container');
    
    if (!newsArray || newsArray.length === 0) {
        container.innerHTML = `
            <div class="no-news">
                <h3>📭 Новостей пока нет</h3>
                <p>Система автоматически собирает новости. Обычно это занимает 1-2 минуты.</p>
                <div class="setup-steps">
                    <div class="setup-step">
                        <span class="step-icon">🔄</span>
                        <span class="step-text">Автоматический сбор запущен</span>
                    </div>
                    <div class="setup-step">
                        <span class="step-icon">⏳</span>
                        <span class="step-text">Ожидаем завершения сбора</span>
                    </div>
                    <div class="setup-step">
                        <span class="step-icon">📊</span>
                        <span class="step-text">Данные появятся автоматически</span>
                    </div>
                </div>
                <div class="no-news-actions">
                    <button onclick="collectNow()" class="btn btn-primary">🚀 Запустить сбор</button>
                    <button onclick="loadNews()" class="btn btn-secondary">🔄 Проверить снова</button>
                </div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = newsArray.map(news => `
        <div class="news-card">
            <div class="news-header">
                <span class="category-tag">${news.category}</span>
                <span class="impact-badge impact-${news.impact_level}">${news.impact_level} приоритет</span>
            </div>
            <div class="news-source">📰 ${news.source}</div>
            <div class="hotness-indicator">
                <div class="hotness-bar">
                    <div class="hotness-fill" style="width: ${Math.round(news.hotness * 100)}%"></div>
                </div>
                <div class="hotness-score">${news.hotness.toFixed(2)}</div>
            </div>
            <h2>${news.headline}</h2>
            <p class="why-now">${news.why_now}</p>
            <div class="entities-preview">
                ${(news.entities || []).slice(0, 4).map(entity => `
                    <span class="entity-tag">${entity}</span>
                `).join('')}
                ${(news.entities || []).length > 4 ? `<span class="entity-more">+${(news.entities || []).length - 4}</span>` : ''}
            </div>
            <div class="news-actions">
                <a href="/news/${news.id}" class="btn btn-secondary">Анализ и черновик →</a>
            </div>
        </div>
    `).join('');
}

function updateStats(newsArray) {
    const totalNews = document.getElementById('total-news');
    const highPriority = document.getElementById('high-priority');
    const financeNews = document.getElementById('finance-news');
    
    if (totalNews) totalNews.textContent = newsArray.length;
    
    if (highPriority) {
        const highCount = newsArray.filter(news => news.impact_level === 'высокий').length;
        highPriority.textContent = highCount;
    }
    
    if (financeNews) {
        const financeCount = newsArray.filter(news => news.category === 'finance').length;
        financeNews.textContent = financeCount;
    }
}

async function collectNow() {
    const btn = document.getElementById('collect-now-btn');
    const originalText = btn?.textContent || '🚀 Собрать сейчас';
    
    if (btn) {
        btn.disabled = true;
        btn.textContent = '🔄 Собираем...';
    }
    
    try {
        const response = await fetch('/api/collect-now', { method: 'POST' });
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification(result.message, 'success');
            setTimeout(() => {
                loadNews();
                loadSystemStats();
            }, 30000);
        } else {
            showError(result.message || 'Ошибка запуска сбора');
        }
    } catch (error) {
        console.error('Error starting collection:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    const container = document.getElementById('news-container');
    
    if (!loading || !container) return;
    
    if (show) {
        loading.classList.remove('hidden');
        container.classList.add('hidden');
    } else {
        loading.classList.add('hidden');
        container.classList.remove('hidden');
    }
}

function updateLastUpdated() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('ru-RU');
    const element = document.getElementById('last-update-time');
    if (element) {
        element.textContent = timeString;
    }
}

async function refreshNews() {
    const btn = document.getElementById('refresh-btn');
    if (!btn) return;
    
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = '🔍 Сканируем...';
    
    try {
        const response = await fetch('/api/refresh', { method: 'POST' });
        const result = await response.json();
        
        if (result.status === 'success') {
            window.updateCount++;
            await loadNews();
            loadSystemStats();
            showNotification(`Обновлено ${result.news_count || 0} новостей`, 'success');
        } else if (result.status === 'info') {
            showNotification(result.message, 'info');
        } else {
            showError(result.message || 'Ошибка обновления');
        }
    } catch (error) {
        console.error('Error refreshing news:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function startAutoStatusCheck() {
    setInterval(() => {
        checkSystemStatus();
        loadSystemStats();
    }, 10000);
    
    setInterval(() => {
        if (window.currentNewsData.length === 0) {
            loadNews();
        }
    }, 30000);
}

function showNotification(message, type = 'info') {
    const oldNotifications = document.querySelectorAll('.notification');
    oldNotifications.forEach(notif => notif.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-text">${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function showError(message) {
    showNotification(message, 'error');
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing RADAR System...');
    
    addDynamicStyles();
    
    if (document.getElementById('refresh-btn')) {
        initializeMainPage();
    }
    
    const filter = document.getElementById('priority-filter');
    if (filter) {
        filter.addEventListener('change', loadNews);
    }
});

function addDynamicStyles() {
    if (document.getElementById('radar-dynamic-styles')) return;
    
    const styles = `
        .news-card {
            animation: fadeInUp 0.6s ease;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .status-indicator.collecting {
            animation: pulse 2s infinite;
        }
    `;
    
    const styleSheet = document.createElement('style');
    styleSheet.id = 'radar-dynamic-styles';
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
}

let currentSort = 'hotness';
let currentPriority = 'all';

function initializeSorting() {
    const sortSelect = document.getElementById('sort-select');
    const prioritySelect = document.getElementById('priority-select');
    
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            currentSort = this.value;
            loadNews();
        });
    }
    
    if (prioritySelect) {
        prioritySelect.addEventListener('change', function() {
            currentPriority = this.value;
            loadNews();
        });
    }
}

async function loadNews() {
    showLoading(true);
    
    try {
        const url = `/api/news?hours=24&limit=20&sort=${currentSort}&priority=${currentPriority}`;
        
        console.log('Loading news with sorting:', { sort: currentSort, priority: currentPriority });
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('News response with sorting:', data);
        
        if (data.status === 'error') {
            showError(data.message || 'Ошибка загрузки новостей');
        } else if (data.status === 'no_data') {
            showNotification(data.message, 'info');
        }
        
        window.currentNewsData = data.news || [];
        displayNews(data.news || []);
        updateStats(data.news || []);
        updateLastUpdated();
        
        updateSortingInfo(data.sorting);
        
    } catch (error) {
        console.error('Error loading news:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        showLoading(false);
    }
}

function updateSortingInfo(sortingInfo) {
    const sortingInfoElement = document.getElementById('sorting-info');
    if (!sortingInfoElement || !sortingInfo) return;
    
    const priorityStats = sortingInfo.priority_stats || {};
    
    sortingInfoElement.innerHTML = `
        <div class="sorting-stats">
            <span>📊 Сортировка: ${getSortLabel(sortingInfo.current_sort)}</span>
            <span>🎯 Приоритет: ${getPriorityLabel(sortingInfo.current_priority)}</span>
            <span class="priority-badges">
                <span class="priority-badge high">🔥 ${priorityStats.high || 0}</span>
                <span class="priority-badge medium">📈 ${priorityStats.medium || 0}</span>
                <span class="priority-badge low">📊 ${priorityStats.low || 0}</span>
            </span>
        </div>
    `;
}

function getSortLabel(sort) {
    const labels = {
        'hotness': 'По важности',
        'date_new': 'По дате (новые)',
        'date_old': 'По дате (старые)',
        'source': 'По источнику'
    };
    return labels[sort] || sort;
}

function getPriorityLabel(priority) {
    const labels = {
        'all': 'Все',
        'high': 'Высокий',
        'medium': 'Средний',
        'low': 'Низкий'
    };
    return labels[priority] || priority;
}

function displayNews(newsArray) {
    const container = document.getElementById('news-container');
    
    if (!newsArray || newsArray.length === 0) {
        container.innerHTML = `
            <div class="no-news">
                <h3>📭 Новостей пока нет</h3>
                <p>Попробуйте изменить фильтры или запустить сбор новостей.</p>
                <div class="no-news-actions">
                    <button onclick="collectNow()" class="btn btn-primary">🚀 Запустить сбор</button>
                    <button onclick="loadNews()" class="btn btn-secondary">🔄 Обновить</button>
                </div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = newsArray.map(news => `
        <div class="news-card priority-${getPriorityClass(news.hotness)}">
            <div class="news-header">
                <span class="category-tag">${news.category}</span>
                <span class="impact-badge impact-${news.impact_level}">
                    ${getPriorityIcon(news.hotness)} ${news.impact_level} приоритет
                </span>
            </div>
            <div class="news-source">📰 ${news.source}</div>
            <div class="hotness-indicator">
                <div class="hotness-bar">
                    <div class="hotness-fill" style="width: ${Math.round(news.hotness * 100)}%"></div>
                </div>
                <div class="hotness-score">${news.hotness.toFixed(2)}</div>
            </div>
            <h2>${news.headline}</h2>
            <p class="why-now">${news.why_now}</p>
            <div class="entities-preview">
                ${(news.entities || []).slice(0, 4).map(entity => `
                    <span class="entity-tag">${entity}</span>
                `).join('')}
                ${(news.entities || []).length > 4 ? `<span class="entity-more">+${(news.entities || []).length - 4}</span>` : ''}
            </div>
            <div class="news-actions">
                <a href="/news/${news.id}" class="btn btn-secondary">Анализ и черновик →</a>
            </div>
        </div>
    `).join('');
}

function getPriorityClass(hotness) {
    if (hotness > 0.7) return 'high';
    if (hotness > 0.4) return 'medium';
    return 'low';
}

function getPriorityIcon(hotness) {
    if (hotness > 0.7) return '🔥';
    if (hotness > 0.4) return '📈';
    return '📊';
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing RADAR System with sorting...');
    
    addDynamicStyles();
    
    if (document.getElementById('refresh-btn')) {
        initializeMainPage();
        initializeSorting(); 
    }
});