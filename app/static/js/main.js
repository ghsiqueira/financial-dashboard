// === CONFIGURAÇÕES GLOBAIS ===
const CONFIG = {
    currency: 'BRL',
    locale: 'pt-BR',
    apiEndpoints: {
        transactions: '/transactions/api',
        dashboard: '/dashboard/api',
        family: '/family/api'
    }
};

// === UTILITÁRIOS ===
const Utils = {
    // Formatar moeda
    formatCurrency(amount) {
        return new Intl.NumberFormat(CONFIG.locale, {
            style: 'currency',
            currency: CONFIG.currency
        }).format(amount);
    },

    // Formatar data
    formatDate(date) {
        return new Intl.DateTimeFormat(CONFIG.locale).format(new Date(date));
    },

    // Formatar data e hora
    formatDateTime(date) {
        return new Intl.DateTimeFormat(CONFIG.locale, {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    },

    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Mostrar loading
    showLoading(element) {
        const loadingHtml = '<div class="loading"></div>';
        if (typeof element === 'string') {
            document.querySelector(element).innerHTML = loadingHtml;
        } else {
            element.innerHTML = loadingHtml;
        }
    },

    // Remover loading
    hideLoading(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        const loadingEl = element.querySelector('.loading');
        if (loadingEl) {
            loadingEl.remove();
        }
    }
};

// === NOTIFICAÇÕES ===
const Notifications = {
    show(message, type = 'info', duration = 5000) {
        const toastContainer = this.getToastContainer();
        const toast = this.createToast(message, type);
        
        toastContainer.appendChild(toast);
        
        // Mostrar toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remover após duração
        setTimeout(() => {
            toast.remove();
        }, duration);
    },

    success(message) {
        this.show(message, 'success');
    },

    error(message) {
        this.show(message, 'danger');
    },

    warning(message) {
        this.show(message, 'warning');
    },

    info(message) {
        this.show(message, 'info');
    },

    getToastContainer() {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    },

    createToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        return toast;
    }
};

// === API HELPER ===
const API = {
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro na requisição');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    async get(url) {
        return this.request(url);
    },

    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }
};

// === FORMULÁRIOS ===
const Forms = {
    // Validar formulário
    validate(form) {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.showFieldError(input, 'Este campo é obrigatório');
                isValid = false;
            } else {
                this.clearFieldError(input);
            }
        });

        return isValid;
    },

    // Mostrar erro no campo
    showFieldError(input, message) {
        input.classList.add('is-invalid');
        
        let feedback = input.parentNode.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.parentNode.appendChild(feedback);
        }
        feedback.textContent = message;
    },

    // Limpar erro do campo
    clearFieldError(input) {
        input.classList.remove('is-invalid');
        const feedback = input.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    },

    // Submeter formulário via AJAX
    async submit(form, url = null) {
        if (!this.validate(form)) {
            return false;
        }

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        try {
            const submitUrl = url || form.action;
            const result = await API.post(submitUrl, data);
            
            if (result.success) {
                Notifications.success(result.message || 'Operação realizada com sucesso!');
                return result;
            } else {
                Notifications.error(result.error || 'Erro na operação');
                return false;
            }
        } catch (error) {
            Notifications.error(error.message);
            return false;
        }
    }
};

// === CHARTS ===
const Charts = {
    // Configurações padrão do Plotly
    defaultConfig: {
        responsive: true,
        displayModeBar: false,
        locale: 'pt-BR'
    },

    defaultLayout: {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
            family: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'
        },
        margin: {
            l: 50,
            r: 50,
            t: 50,
            b: 50
        }
    },

    // Renderizar gráfico
    render(elementId, data, layout = {}, config = {}) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element with id '${elementId}' not found`);
            return;
        }

        const finalLayout = { ...this.defaultLayout, ...layout };
        const finalConfig = { ...this.defaultConfig, ...config };

        Plotly.newPlot(elementId, data, finalLayout, finalConfig);
    },

    // Atualizar gráfico
    update(elementId, data, layout = {}) {
        Plotly.react(elementId, data, layout);
    },

    // Limpar gráfico
    clear(elementId) {
        Plotly.purge(elementId);
    }
};

// === DASHBOARD ===
const Dashboard = {
    // Carregar dados do dashboard
    async loadData(accountType = 'individual') {
        try {
            const data = await API.get(`${CONFIG.apiEndpoints.dashboard}/summary?account=${accountType}`);
            this.updateSummaryCards(data);
            return data;
        } catch (error) {
            Notifications.error('Erro ao carregar dados do dashboard');
        }
    },

    // Atualizar cards de resumo
    updateSummaryCards(data) {
        const elements = {
            income: document.getElementById('total-income'),
            expense: document.getElementById('total-expense'),
            balance: document.getElementById('balance')
        };

        if (elements.income) {
            elements.income.textContent = Utils.formatCurrency(data.income || 0);
        }
        if (elements.expense) {
            elements.expense.textContent = Utils.formatCurrency(data.expense || 0);
        }
        if (elements.balance) {
            elements.balance.textContent = Utils.formatCurrency(data.balance || 0);
            
            // Mudar cor baseado no saldo
            const balanceCard = elements.balance.closest('.card');
            if (balanceCard) {
                balanceCard.className = balanceCard.className.replace(/stats-card\s\w+/, 'stats-card');
                if (data.balance > 0) {
                    balanceCard.classList.add('income');
                } else if (data.balance < 0) {
                    balanceCard.classList.add('expense');
                } else {
                    balanceCard.classList.add('balance');
                }
            }
        }
    },

    // Carregar gráficos
    async loadCharts(accountType = 'individual') {
        const chartTypes = ['expenses_by_category', 'monthly_evolution', 'income_vs_expenses'];
        
        for (const chartType of chartTypes) {
            try {
                const data = await API.get(`${CONFIG.apiEndpoints.dashboard}/charts/${chartType}?account=${accountType}`);
                this.renderChart(chartType, data);
            } catch (error) {
                console.error(`Erro ao carregar gráfico ${chartType}:`, error);
            }
        }
    },

    // Renderizar gráfico específico
    renderChart(chartType, data) {
        const elementId = `chart-${chartType.replace(/_/g, '-')}`;
        
        switch (chartType) {
            case 'expenses_by_category':
                this.renderPieChart(elementId, data);
                break;
            case 'monthly_evolution':
                this.renderLineChart(elementId, data);
                break;
            case 'income_vs_expenses':
                this.renderBarChart(elementId, data);
                break;
        }
    },

    // Gráfico de pizza
    renderPieChart(elementId, data) {
        const chartData = [{
            type: 'pie',
            labels: data.labels,
            values: data.values,
            hovertemplate: '<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}<extra></extra>',
            textinfo: 'label+percent',
            textposition: 'outside'
        }];

        Charts.render(elementId, chartData, {
            title: 'Gastos por Categoria'
        });
    },

    // Gráfico de linha
    renderLineChart(elementId, data) {
        const chartData = [
            {
                x: data.labels,
                y: data.income,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Receitas',
                line: { color: '#28a745', width: 3 },
                marker: { size: 8 }
            },
            {
                x: data.labels,
                y: data.expenses,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Despesas',
                line: { color: '#dc3545', width: 3 },
                marker: { size: 8 }
            }
        ];

        Charts.render(elementId, chartData, {
            title: 'Evolução Mensal',
            xaxis: { title: 'Mês' },
            yaxis: { title: 'Valor (R$)' }
        });
    },

    // Gráfico de barras
    renderBarChart(elementId, data) {
        const chartData = [{
            x: data.labels,
            y: data.values,
            type: 'bar',
            marker: {
                color: data.labels.map(label => 
                    label.toLowerCase().includes('receita') ? '#28a745' : '#dc3545'
                )
            }
        }];

        Charts.render(elementId, chartData, {
            title: 'Receitas vs Despesas'
        });
    }
};

// === TRANSAÇÕES ===
const Transactions = {
    // Carregar transações recentes
    async loadRecent(limit = 10, accountType = 'individual') {
        try {
            const data = await API.get(`${CONFIG.apiEndpoints.transactions}/recent?limit=${limit}&account=${accountType}`);
            this.renderRecentTransactions(data);
            return data;
        } catch (error) {
            Notifications.error('Erro ao carregar transações');
        }
    },

    // Renderizar transações recentes
    renderRecentTransactions(transactions) {
        const container = document.getElementById('recent-transactions');
        if (!container) return;

        if (!transactions || transactions.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhuma transação encontrada</p>';
            return;
        }

        const html = transactions.map(transaction => `
            <div class="transaction-item ${transaction.type} p-3 mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${transaction.description || 'Sem descrição'}</h6>
                        <small class="text-muted">${transaction.category} • ${Utils.formatDate(transaction.date)}</small>
                    </div>
                    <div class="text-end">
                        <span class="transaction-amount ${transaction.type}">
                            ${transaction.type === 'income' ? '+' : '-'}${Utils.formatCurrency(transaction.amount)}
                        </span>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    },

    // Deletar transação
    async delete(transactionId) {
        if (!confirm('Tem certeza que deseja excluir esta transação?')) {
            return false;
        }

        try {
            await API.delete(`${CONFIG.apiEndpoints.transactions}/${transactionId}`);
            Notifications.success('Transação excluída com sucesso!');
            
            // Remover da tabela
            const row = document.querySelector(`tr[data-transaction-id="${transactionId}"]`);
            if (row) {
                row.remove();
            }
            
            // Recarregar dados
            Dashboard.loadData();
            
            return true;
        } catch (error) {
            Notifications.error('Erro ao excluir transação');
            return false;
        }
    }
};

// === FAMÍLIA ===
const Family = {
    // Trocar família ativa
    async switchFamily(familyId) {
        try {
            window.location.href = `/family/switch/${familyId}`;
        } catch (error) {
            Notifications.error('Erro ao trocar família');
        }
    },

    // Sair da família
    async leave(familyId) {
        if (!confirm('Tem certeza que deseja sair desta família?')) {
            return false;
        }

        try {
            await API.post(`/family/leave/${familyId}`);
            Notifications.success('Você saiu da família');
            window.location.reload();
            return true;
        } catch (error) {
            Notifications.error('Erro ao sair da família');
            return false;
        }
    },

    // Remover membro
    async removeMember(familyId, memberId) {
        if (!confirm('Tem certeza que deseja remover este membro?')) {
            return false;
        }

        try {
            await API.post('/family/remove_member', {
                family_id: familyId,
                member_id: memberId
            });
            
            Notifications.success('Membro removido com sucesso');
            
            // Remover da lista
            const memberCard = document.querySelector(`[data-member-id="${memberId}"]`);
            if (memberCard) {
                memberCard.remove();
            }
            
            return true;
        } catch (error) {
            Notifications.error('Erro ao remover membro');
            return false;
        }
    },

    // Alterar papel do membro
    async changeRole(familyId, memberId, newRole) {
        try {
            await API.post('/family/change_role', {
                family_id: familyId,
                member_id: memberId,
                role: newRole
            });
            
            Notifications.success('Papel alterado com sucesso');
            window.location.reload();
            
            return true;
        } catch (error) {
            Notifications.error('Erro ao alterar papel');
            return false;
        }
    }
};

// === INICIALIZAÇÃO ===
document.addEventListener('DOMContentLoaded', function() {
    // Auto-submit de formulários com classe 'auto-submit'
    document.querySelectorAll('form.auto-submit').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const result = await Forms.submit(this);
            if (result && result.redirect) {
                window.location.href = result.redirect;
            }
        });
    });

    // Auto-dismiss de alertas após 5 segundos
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Carregar dados da página atual
    const currentPage = document.body.getAttribute('data-page');
    
    switch (currentPage) {
        case 'dashboard':
            Dashboard.loadData();
            Dashboard.loadCharts();
            Transactions.loadRecent();
            break;
        case 'transactions':
            // Inicializar filtros e paginação
            break;
        case 'family':
            // Inicializar funcionalidades da família
            break;
    }

    // Inicializar tooltips do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicializar popovers do Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Exportar para uso global
window.FinanceDash = {
    Utils,
    Notifications,
    API,
    Forms,
    Charts,
    Dashboard,
    Transactions,
    Family
};