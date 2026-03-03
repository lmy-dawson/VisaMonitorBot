// API Configuration
const API_BASE = '/api/v1';

// State
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// Loading state helpers
function setButtonLoading(button, loading) {
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
        if (button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
        }
    }
}

function showPageLoader(message = 'Loading...') {
    let loader = document.getElementById('pageLoader');
    if (!loader) {
        loader = document.createElement('div');
        loader.id = 'pageLoader';
        loader.className = 'page-loader';
        loader.innerHTML = `<div class="spinner"></div><p>${message}</p>`;
        document.body.appendChild(loader);
    } else {
        loader.querySelector('p').textContent = message;
        loader.classList.remove('hidden');
    }
}

function hidePageLoader() {
    const loader = document.getElementById('pageLoader');
    if (loader) {
        loader.classList.add('hidden');
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'toast-in 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Embassy display names
const EMBASSY_NAMES = {
    'us_accra': '🇺🇸 US Embassy - Accra',
    'us_lagos': '🇺🇸 US Embassy - Lagos',
    'uk_vfs_accra': '🇬🇧 UK Visa (VFS) - Accra',
    'uk_vfs_lagos': '🇬🇧 UK Visa (VFS) - Lagos',
    'schengen_accra': '🇪🇺 Schengen - Accra',
    'custom': '🔗 Custom URL'
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        showPageLoader('Loading your dashboard...');
        loadUserProfile();
    } else {
        showLoggedOutState();
    }
});

// API Helper
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        logout();
        throw new Error('Session expired. Please login again.');
    }
    
    return response;
}

// Auth Functions
async function handleRegister(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const errorEl = document.getElementById('registerError');
    errorEl.classList.add('hidden');
    
    const data = {
        email: form.email.value,
        password: form.password.value,
        phone: form.phone.value || null,
        notification_preference: 'telegram'
    };
    
    setButtonLoading(button, true);
    
    try {
        const response = await apiRequest('/users/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }
        
        showToast('Account created! Logging you in...', 'success');
        
        // Auto-login after registration
        await doLogin(data.email, data.password);
        
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
        showToast(error.message, 'error');
    } finally {
        setButtonLoading(button, false);
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const errorEl = document.getElementById('loginError');
    errorEl.classList.add('hidden');
    
    setButtonLoading(button, true);
    
    try {
        await doLogin(form.email.value, form.password.value);
        showToast('Welcome back!', 'success');
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
        showToast(error.message, 'error');
    } finally {
        setButtonLoading(button, false);
    }
}

async function doLogin(email, password) {
    const response = await apiRequest('/users/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
    }
    
    const data = await response.json();
    authToken = data.access_token;
    localStorage.setItem('authToken', authToken);
    
    await loadUserProfile();
    closeModals();
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    showLoggedOutState();
}

async function loadUserProfile() {
    try {
        const response = await apiRequest('/users/me');
        
        if (!response.ok) {
            throw new Error('Failed to load profile');
        }
        
        currentUser = await response.json();
        showLoggedInState();
        loadMonitors();
        loadAlerts();
        
    } catch (error) {
        console.error('Failed to load profile:', error);
        logout();
    } finally {
        hidePageLoader();
    }
}

// UI State Functions
function showLoggedOutState() {
    document.getElementById('authNav').classList.remove('hidden');
    document.getElementById('userNav').classList.add('hidden');
    document.getElementById('heroSection').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('how-it-works').classList.remove('hidden');
    document.querySelector('.embassies-section').classList.remove('hidden');
}

function showLoggedInState() {
    document.getElementById('authNav').classList.add('hidden');
    document.getElementById('userNav').classList.remove('hidden');
    document.getElementById('userEmail').textContent = currentUser.email;
    document.getElementById('heroSection').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('how-it-works').classList.add('hidden');
    document.querySelector('.embassies-section').classList.add('hidden');
    
    // Show telegram banner if not connected, otherwise show test alert banner
    const telegramBanner = document.getElementById('telegramBanner');
    const testAlertBanner = document.getElementById('testAlertBanner');
    if (!currentUser.telegram_chat_id) {
        telegramBanner.classList.remove('hidden');
        testAlertBanner.classList.add('hidden');
    } else {
        telegramBanner.classList.add('hidden');
        testAlertBanner.classList.remove('hidden');
    }
    
    // Load monitoring status
    fetchMonitoringStatus();
}

// Modal Functions
function showLogin() {
    closeModals();
    document.getElementById('loginModal').classList.remove('hidden');
}

function showRegister() {
    closeModals();
    document.getElementById('registerModal').classList.remove('hidden');
}

function showTelegramSetup() {
    closeModals();
    document.getElementById('telegramModal').classList.remove('hidden');
}

function showAddMonitor() {
    closeModals();
    document.getElementById('monitorModal').classList.remove('hidden');
}

function closeModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    // Reset forms
    document.querySelectorAll('.form-error, .form-success').forEach(el => el.classList.add('hidden'));
}

// Close modal on backdrop click
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModals();
        }
    });
});

// Telegram Setup
async function handleTelegramSetup(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const errorEl = document.getElementById('telegramError');
    const successEl = document.getElementById('telegramSuccess');
    errorEl.classList.add('hidden');
    successEl.classList.add('hidden');
    
    setButtonLoading(button, true);
    
    try {
        const response = await apiRequest('/users/telegram/setup', {
            method: 'POST',
            body: JSON.stringify({
                telegram_chat_id: form.chat_id.value
            })
        });
        
        const data = await response.json();
        
        if (data.verified) {
            successEl.textContent = data.message;
            successEl.classList.remove('hidden');
            currentUser.telegram_chat_id = form.chat_id.value;
            document.getElementById('telegramBanner').classList.add('hidden');
            document.getElementById('testAlertBanner').classList.remove('hidden');
            showToast('Telegram connected successfully!', 'success');
            
            setTimeout(() => {
                closeModals();
            }, 2000);
        } else {
            throw new Error(data.message);
        }
        
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
        showToast(error.message, 'error');
    } finally {
        setButtonLoading(button, false);
    }
}

// Test Alert
async function sendTestAlert() {
    const btn = event.target;
    setButtonLoading(btn, true);
    
    try {
        const response = await apiRequest('/alerts/test', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setButtonLoading(btn, false);
            btn.innerHTML = '✓ Sent! Check Telegram';
            btn.classList.add('btn-success');
            showToast('Test alert sent! Check your Telegram.', 'success');
            // Reload alerts to show the test alert
            loadAlerts();
            setTimeout(() => {
                btn.innerHTML = '🔔 Send Test Alert';
                btn.classList.remove('btn-success');
            }, 3000);
        } else {
            throw new Error(data.detail || 'Failed to send test alert');
        }
        
    } catch (error) {
        setButtonLoading(btn, false);
        btn.innerHTML = '✗ ' + error.message;
        btn.classList.add('btn-danger');
        showToast(error.message, 'error');
        setTimeout(() => {
            btn.innerHTML = '🔔 Send Test Alert';
            btn.classList.remove('btn-danger');
        }, 3000);
    }
}

// Monitors
async function loadMonitors() {
    try {
        const response = await apiRequest('/monitors');
        const monitors = await response.json();
        
        const container = document.getElementById('monitorsList');
        const empty = document.getElementById('emptyMonitors');
        
        if (monitors.length === 0) {
            container.classList.add('hidden');
            empty.classList.remove('hidden');
            return;
        }
        
        container.classList.remove('hidden');
        empty.classList.add('hidden');
        
        container.innerHTML = monitors.map(monitor => `
            <div class="monitor-card ${monitor.is_active ? '' : 'paused'}">
                <div class="monitor-header">
                    <span class="monitor-embassy">${EMBASSY_NAMES[monitor.embassy] || monitor.embassy}</span>
                    <span class="monitor-status ${monitor.is_active ? 'active' : 'paused'}">
                        ${monitor.is_active ? '● Active' : '○ Paused'}
                    </span>
                </div>
                <div class="monitor-details">
                    ${monitor.visa_type ? `<div>Visa Type: ${monitor.visa_type}</div>` : ''}
                    ${monitor.preferred_date_from ? `<div>From: ${formatDate(monitor.preferred_date_from)}</div>` : ''}
                    ${monitor.preferred_date_to ? `<div>To: ${formatDate(monitor.preferred_date_to)}</div>` : ''}
                </div>
                <div class="monitor-actions">
                    ${monitor.is_active 
                        ? `<button class="btn btn-outline btn-sm" onclick="pauseMonitor(${monitor.id})">Pause</button>`
                        : `<button class="btn btn-success btn-sm" onclick="resumeMonitor(${monitor.id})">Resume</button>`
                    }
                    <button class="btn btn-danger btn-sm" onclick="deleteMonitor(${monitor.id})">Delete</button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load monitors:', error);
    }
}

async function handleAddMonitor(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const errorEl = document.getElementById('monitorError');
    errorEl.classList.add('hidden');
    
    const embassy = form.embassy.value;
    const customUrl = form.custom_url?.value || null;
    
    // Validate custom URL if custom embassy selected
    if (embassy === 'custom' && !customUrl) {
        errorEl.textContent = 'Please enter a custom URL to monitor';
        errorEl.classList.remove('hidden');
        return;
    }
    
    const data = {
        embassy: embassy,
        custom_url: embassy === 'custom' ? customUrl : null,
        visa_type: form.visa_type.value || null,
        preferred_date_from: form.date_from.value ? new Date(form.date_from.value).toISOString() : null,
        preferred_date_to: form.date_to.value ? new Date(form.date_to.value).toISOString() : null
    };
    
    setButtonLoading(button, true);
    
    try {
        const response = await apiRequest('/monitors', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create monitor');
        }
        
        showToast('Monitor created successfully!', 'success');
        closeModals();
        form.reset();
        document.getElementById('customUrlGroup').style.display = 'none';
        loadMonitors();
        fetchMonitoringStatus();
        
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove('hidden');
        showToast(error.message, 'error');
    } finally {
        setButtonLoading(button, false);
    }
}

async function pauseMonitor(id) {
    const btn = event.target;
    setButtonLoading(btn, true);
    try {
        await apiRequest(`/monitors/${id}/pause`, { method: 'POST' });
        showToast('Monitor paused', 'info');
        loadMonitors();
    } catch (error) {
        showToast('Failed to pause monitor', 'error');
    }
}

async function resumeMonitor(id) {
    const btn = event.target;
    setButtonLoading(btn, true);
    try {
        await apiRequest(`/monitors/${id}/resume`, { method: 'POST' });
        showToast('Monitor resumed', 'success');
        loadMonitors();
    } catch (error) {
        showToast('Failed to resume monitor', 'error');
    }
}

async function deleteMonitor(id) {
    if (!confirm('Are you sure you want to delete this monitor?')) return;
    
    const btn = event.target;
    setButtonLoading(btn, true);
    try {
        await apiRequest(`/monitors/${id}`, { method: 'DELETE' });
        showToast('Monitor deleted', 'info');
        loadMonitors();
    } catch (error) {
        showToast('Failed to delete monitor', 'error');
        setButtonLoading(btn, false);
    }
}

// Alerts
async function loadAlerts() {
    try {
        const response = await apiRequest('/alerts?limit=10');
        const alerts = await response.json();
        
        const container = document.getElementById('alertsList');
        const empty = document.getElementById('emptyAlerts');
        
        if (alerts.length === 0) {
            container.classList.add('hidden');
            empty.classList.remove('hidden');
            return;
        }
        
        container.classList.remove('hidden');
        empty.classList.add('hidden');
        
        container.innerHTML = alerts.map(alert => `
            <div class="alert-item ${alert.booked ? 'booked' : ''}">
                <div class="alert-info">
                    <div class="alert-embassy">${EMBASSY_NAMES[alert.embassy] || alert.embassy}</div>
                    <div class="alert-date">
                        ${formatDateTime(alert.sent_at)}
                        ${alert.booked ? ' • ✅ Booked' : ''}
                    </div>
                </div>
                <div class="alert-actions">
                    ${!alert.booked 
                        ? `<button class="btn btn-success btn-sm" onclick="markBooked(${alert.id})">Mark Booked</button>`
                        : ''
                    }
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load alerts:', error);
    }
}

async function markBooked(id) {
    const btn = event.target;
    setButtonLoading(btn, true);
    try {
        await apiRequest(`/alerts/${id}/booked`, {
            method: 'PATCH',
            body: JSON.stringify({ booked: true })
        });
        showToast('Marked as booked! Congratulations! 🎉', 'success');
        loadAlerts();
        loadMonitors(); // Refresh monitors as they may be paused
    } catch (error) {
        showToast('Failed to mark as booked', 'error');
        setButtonLoading(btn, false);
    }
}

// Utility Functions
function formatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString();
}

function formatDateTime(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString();
}

// Toggle custom URL field
function toggleCustomUrl(select) {
    const customUrlGroup = document.getElementById('customUrlGroup');
    const customUrlInput = document.getElementById('customUrlInput');
    
    if (select.value === 'custom') {
        customUrlGroup.style.display = 'block';
        customUrlInput.required = true;
    } else {
        customUrlGroup.style.display = 'none';
        customUrlInput.required = false;
        customUrlInput.value = '';
    }
}

// Fetch and display monitoring status
async function fetchMonitoringStatus() {
    try {
        const response = await apiRequest('/monitors/status/overview');
        
        if (!response.ok) {
            console.error('Failed to fetch monitoring status');
            return;
        }
        
        const status = await response.json();
        
        // Update status badge
        const statusBadge = document.getElementById('statusBadge');
        if (status.is_monitoring) {
            statusBadge.textContent = 'Active';
            statusBadge.style.background = '#dcfce7';
            statusBadge.style.color = '#166534';
        } else {
            statusBadge.textContent = 'No monitors';
            statusBadge.style.background = '#fef3c7';
            statusBadge.style.color = '#92400e';
        }
        
        // Update status details
        document.getElementById('activeMonitorsCount').textContent = 
            `${status.active_monitors} of ${status.total_monitors}`;
        
        document.getElementById('checkInterval').textContent = 
            `Every ${status.check_interval_minutes} min`;
        
        if (status.last_checked_at) {
            const lastCheck = new Date(status.last_checked_at);
            const now = new Date();
            const diffMins = Math.round((now - lastCheck) / 60000);
            document.getElementById('lastCheckTime').textContent = 
                diffMins < 1 ? 'Just now' : `${diffMins} min ago`;
        } else {
            document.getElementById('lastCheckTime').textContent = 'Never';
        }
        
        if (status.next_check_at) {
            const nextCheck = new Date(status.next_check_at);
            const now = new Date();
            const diffMins = Math.round((nextCheck - now) / 60000);
            document.getElementById('nextCheckTime').textContent = 
                diffMins <= 0 ? 'Soon' : `In ${diffMins} min`;
        } else {
            document.getElementById('nextCheckTime').textContent = '-';
        }
        
    } catch (error) {
        console.error('Failed to fetch monitoring status:', error);
    }
}

// Auto-refresh monitoring status every 30 seconds
setInterval(() => {
    if (authToken && currentUser) {
        fetchMonitoringStatus();
    }
}, 30000);