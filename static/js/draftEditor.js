class DraftEditor {
    constructor() {
        this.currentDraft = null;
        this.isEditing = false;
        this.currentNewsId = null;
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('edit-draft-btn')) {
                this.startEditing(parseInt(e.target.dataset.newsId));
            }
            
            if (e.target.classList.contains('save-draft-btn')) {
                this.saveDraft();
            }
            
            if (e.target.classList.contains('cancel-edit-btn')) {
                this.cancelEditing();
            }
            
            if (e.target.classList.contains('use-template-btn')) {
                this.applyTemplate();
            }
            
            if (e.target.classList.contains('editor-modal')) {
                this.cancelEditing();
            }
        });

        document.addEventListener('input', (e) => {
            if (this.isEditing && e.target.classList.contains('draft-field')) {
                this.autoSave();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (this.isEditing && e.key === 'Escape') {
                this.cancelEditing();
            }
        });
    }

    async startEditing(newsId) {
        this.isEditing = true;
        this.currentNewsId = newsId;
        
        try {
            const response = await fetch(`/api/get-draft/${newsId}`);
            const draftData = await response.json();
            this.currentDraft = draftData;
            this.showEditor();
            this.populateForm();
        } catch (error) {
            console.error('Error loading draft:', error);
            this.showNotification('Ошибка загрузки черновика', 'error');
        }
    }

    showEditor() {
        const editorHTML = `
            <div class="editor-modal">
                <div class="editor-container">
                    <div class="editor-header">
                        <h2>✍️ Редактор черновика</h2>
                        <div class="editor-actions">
                            <button class="btn btn-secondary use-template-btn">📝 Шаблон</button>
                            <button class="btn btn-secondary cancel-edit-btn">❌ Отмена</button>
                            <button class="btn btn-primary save-draft-btn">💾 Сохранить</button>
                        </div>
                    </div>
                    
                    <div class="editor-content">
                        <div class="form-group">
                            <label>Заголовок:</label>
                            <input type="text" class="draft-field" data-field="title" placeholder="Введите заголовок...">
                        </div>
                        
                        <div class="form-group">
                            <label>Лид-абзац:</label>
                            <textarea class="draft-field" data-field="lead" rows="3" placeholder="Введите вводный абзац..."></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Ключевые пункты (каждый с новой строки):</label>
                            <div class="bullets-editor">
                                <textarea class="draft-field" data-field="bullets" rows="6" placeholder="Введите каждый пункт с новой строки..."></textarea>
                                <small>Каждый пункт будет отображаться как отдельный буллет-поинт</small>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Цитата:</label>
                            <textarea class="draft-field" data-field="quote" rows="2" placeholder="Введите важную цитату..."></textarea>
                        </div>
                    </div>
                    
                    <div class="editor-preview">
                        <h3>📊 Предпросмотр:</h3>
                        <div class="preview-content" id="draft-preview"></div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', editorHTML);
    }

    populateForm() {
        if (!this.currentDraft) return;

        const fields = {
            'title': this.currentDraft.title || '',
            'lead': this.currentDraft.lead || '',
            'bullets': Array.isArray(this.currentDraft.bullets) ? this.currentDraft.bullets.join('\n') : '',
            'quote': this.currentDraft.quote || ''
        };

        Object.entries(fields).forEach(([field, value]) => {
            const element = document.querySelector(`[data-field="${field}"]`);
            if (element) element.value = value;
        });
        
        this.updatePreview();
    }

    updatePreview() {
        const preview = document.getElementById('draft-preview');
        if (!preview) return;

        const formData = this.getFormData();
        
        preview.innerHTML = `
            <div class="preview-draft">
                <h4>${formData.title || 'Заголовок'}</h4>
                <p class="preview-lead">${formData.lead || 'Лид-абзац...'}</p>
                <ul class="preview-bullets">
                    ${formData.bullets.map(bullet => bullet ? `<li>${bullet}</li>` : '').join('')}
                </ul>
                <blockquote class="preview-quote">${formData.quote || 'Цитата...'}</blockquote>
            </div>
        `;
    }

    getFormData() {
        const fields = ['title', 'lead', 'bullets', 'quote'];
        const data = {};
        
        fields.forEach(field => {
            const element = document.querySelector(`[data-field="${field}"]`);
            if (element) {
                if (field === 'bullets') {
                    data[field] = element.value.split('\n').filter(b => b.trim());
                } else {
                    data[field] = element.value;
                }
            }
        });
        
        return data;
    }

    autoSave() {
        this.currentDraft = this.getFormData();
        this.updatePreview();
    }

    async saveDraft() {
        try {
            this.currentDraft = this.getFormData();
            
            const response = await fetch(`/api/save-draft/${this.currentNewsId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.currentDraft)
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showNotification('Черновик сохранен!', 'success');
                this.closeEditor();
                
                // Обновл страницу через 1 сек
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                throw new Error(result.message);
            }
            
        } catch (error) {
            console.error('Error saving draft:', error);
            this.showNotification('Ошибка сохранения черновика', 'error');
        }
    }

    applyTemplate() {
        const template = {
            title: "Ключевое событие на финансовых рынках",
            lead: "Значительное развитие ситуации требует внимания инвесторов и аналитиков. Событие может оказать существенное влияние на рыночные котировки и отраслевые тенденции.",
            bullets: [
                "Событие оказало влияние на ключевые активы и сектора",
                "Реакция рынка превысила ожидания аналитиков", 
                "Дальнейшие последствия требуют мониторинга и анализа"
            ],
            quote: "Это важный прецедент для рынка, который может задать новые тренды - ведущий отраслевой эксперт"
        };
        
        this.currentDraft = template;
        this.populateForm();
        this.showNotification('Шаблон применен!', 'info');
    }

    cancelEditing() {
        if (confirm('Отменить изменения? Несохраненные данные будут потеряны.')) {
            this.closeEditor();
        }
    }

    closeEditor() {
        const modal = document.querySelector('.editor-modal');
        if (modal) modal.remove();
        this.isEditing = false;
        this.currentDraft = null;
        this.currentNewsId = null;
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.draftEditor = new DraftEditor();
});
