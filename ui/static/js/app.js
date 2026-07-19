// Bot SIAKAD - BMW-M Dashboard JavaScript
// Complete application logic with loading states, error handling, CSRF

// ============ TOAST NOTIFICATION SYSTEM ============
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// ============ UTILITY FUNCTIONS ============
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function formatTimestamp(date) {
    return new Date(date).toLocaleString('id-ID', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// ============ API HELPER ============
async function apiCall(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': getCsrfToken()
        }
    };
    
    const config = { ...defaults, ...options };
    config.headers = { ...defaults.headers, ...(options.headers || {}) };
    
    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error [${url}]:`, error);
        throw error;
    }
}

// ============ BOT STATUS MONITORING ============
async function updateBotStatus() {
    try {
        const data = await apiCall('/api/status');
        
        // Update footer indicators
        const footerStatus = document.getElementById('footer-status');
        if (footerStatus) {
            footerStatus.textContent = data.status || 'UNKNOWN';
            footerStatus.className = data.status === 'ACTIVE' ? 'status-indicator' : 'status-indicator';
            footerStatus.style.color = data.status === 'ACTIVE' ? 'var(--success)' : 'var(--muted)';
        }
        
        const footerTime = document.getElementById('footer-time');
        if (footerTime) {
            footerTime.textContent = new Date().toLocaleTimeString('id-ID');
        }
        
        const footerSubmit = document.getElementById('footer-submit');
        if (footerSubmit) {
            footerSubmit.textContent = data.allow_submit ? 'ENABLED' : 'DISABLED';
            footerSubmit.className = data.allow_submit ? 'safety-on' : 'safety-off';
        }
        
        const footerFallback = document.getElementById('footer-fallback');
        if (footerFallback) {
            footerFallback.textContent = data.use_fallback ? 'ENABLED' : 'DISABLED';
            footerFallback.className = data.use_fallback ? 'safety-on' : 'safety-off';
        }
        
        // Update dashboard stats
        const botStatusEl = document.getElementById('bot-status');
        if (botStatusEl) {
            botStatusEl.textContent = data.status || 'IDLE';
            const statusDot = botStatusEl.parentElement.querySelector('.status-dot');
            if (statusDot) {
                statusDot.className = `status-dot ${data.status === 'ACTIVE' ? 'active' : 'inactive'}`;
            }
        }
        
        const totalMk = document.getElementById('total-mk');
        if (totalMk) {
            totalMk.textContent = `${data.courses_selected || 0}/${data.courses_total || 8}`;
        }
        
        const totalSks = document.getElementById('total-sks');
        if (totalSks) {
            totalSks.textContent = data.sks_total || 0;
        }
        
        const totalAttempts = document.getElementById('total-attempts');
        if (totalAttempts) {
            totalAttempts.textContent = data.attempts || 0;
        }
        
        // Update control badge
        const controlBadge = document.getElementById('control-badge');
        if (controlBadge) {
            controlBadge.textContent = data.status || 'OFFLINE';
            controlBadge.className = `badge ${data.status === 'ACTIVE' ? 'badge-success' : 'badge-neutral'}`;
        }
        
        // Update safety cards
        const safetySubmit = document.getElementById('safety-submit');
        if (safetySubmit) {
            safetySubmit.textContent = data.allow_submit ? 'ENABLED' : 'DISABLED';
            safetySubmit.className = `badge ${data.allow_submit ? 'badge-danger' : 'badge-neutral'}`;
        }
        
        const safetyFallback = document.getElementById('safety-fallback');
        if (safetyFallback) {
            safetyFallback.textContent = data.use_fallback ? 'ENABLED' : 'DISABLED';
            safetyFallback.className = `badge ${data.use_fallback ? 'badge-warning' : 'badge-neutral'}`;
        }
        
        // Update monitoring page
        if (document.getElementById('uptime')) {
            document.getElementById('uptime').textContent = data.uptime || '00:00:00';
            document.getElementById('success-rate').textContent = `${data.success_rate || 0}%`;
            document.getElementById('current-attempt').textContent = `${data.current_attempt || 0}/${data.max_attempts || 100}`;
            document.getElementById('error-count').textContent = data.errors || 0;
            
            // Update progress
            const progress = data.progress || 0;
            const progressBar = document.getElementById('progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
            }
            const progressPercent = document.getElementById('progress-percent');
            if (progressPercent) {
                progressPercent.textContent = `${progress}%`;
            }
            const progressBadge = document.getElementById('progress-badge');
            if (progressBadge) {
                progressBadge.textContent = `${data.courses_selected || 0}/8 COURSES`;
            }
            
            // Update stage indicators
            const stages = ['login', 'scraping', 'selecting', 'submit'];
            stages.forEach(stage => {
                const indicator = document.getElementById(`status-${stage}`);
                if (indicator) {
                    if (data.current_stage === stage) {
                        indicator.textContent = '●';
                        indicator.style.color = 'var(--m-blue-dark)';
                    } else if (data.completed_stages && data.completed_stages.includes(stage)) {
                        indicator.textContent = '✓';
                        indicator.style.color = 'var(--success)';
                    } else {
                        indicator.textContent = '○';
                        indicator.style.color = 'var(--muted)';
                    }
                }
            });
        }
        
    } catch (error) {
        console.error('Failed to update bot status:', error);
    }
}

// ============ BOT CONTROL FUNCTIONS ============
async function startBot() {
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    
    if (btnStart) {
        btnStart.disabled = true;
        btnStart.classList.add('loading');
    }
    
    try {
        const data = await apiCall('/api/bot/start', { method: 'POST' });
        
        if (data.success) {
            showToast('Bot started successfully', 'success');
            if (btnStart) btnStart.disabled = true;
            if (btnStop) btnStop.disabled = false;
            updateBotStatus();
        } else {
            throw new Error(data.error || 'Failed to start bot');
        }
    } catch (error) {
        showToast('Failed to start bot: ' + error.message, 'error');
        if (btnStart) btnStart.disabled = false;
    } finally {
        if (btnStart) btnStart.classList.remove('loading');
    }
}

async function stopBot() {
    if (!confirm('Are you sure you want to stop the bot?')) return;
    
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    
    if (btnStop) {
        btnStop.disabled = true;
        btnStop.classList.add('loading');
    }
    
    try {
        const data = await apiCall('/api/bot/stop', { method: 'POST' });
        
        if (data.success) {
            showToast('Bot stopped successfully', 'warning');
            if (btnStart) btnStart.disabled = false;
            if (btnStop) btnStop.disabled = true;
            updateBotStatus();
        } else {
            throw new Error(data.error || 'Failed to stop bot');
        }
    } catch (error) {
        showToast('Failed to stop bot: ' + error.message, 'error');
        if (btnStop) btnStop.disabled = false;
    } finally {
        if (btnStop) btnStop.classList.remove('loading');
    }
}

async function dryRun() {
    const btn = document.getElementById('btn-dry-run');
    if (btn) {
        btn.disabled = true;
        btn.classList.add('loading');
    }
    
    try {
        const data = await apiCall('/api/bot/dry-run', { method: 'POST' });
        
        if (data.success) {
            showToast('Dry run completed successfully', 'success');
        } else {
            throw new Error(data.error || 'Dry run failed');
        }
    } catch (error) {
        showToast('Dry run failed: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('loading');
        }
    }
}

async function checkStatus() {
    const btn = document.getElementById('btn-status');
    if (btn) {
        btn.disabled = true;
        btn.classList.add('loading');
    }
    
    try {
        const data = await apiCall('/api/bot/check-status', { method: 'POST' });
        
        if (data.success) {
            showToast(`Status: ${data.status} | Uptime: ${data.uptime}`, 'info');
            updateBotStatus();
        } else {
            throw new Error(data.error || 'Status check failed');
        }
    } catch (error) {
        showToast('Status check failed: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('loading');
        }
    }
}

// ============ ACTIVITY LOG ============
async function loadActivityLog() {
    try {
        const data = await apiCall('/api/activity');
        const activityList = document.getElementById('activity-list');
        
        if (activityList && data.activities) {
            activityList.innerHTML = '';
            
            if (data.activities.length === 0) {
                activityList.innerHTML = `
                    <li class="activity-item">
                        <div class="activity-icon info">ℹ</div>
                        <div class="activity-content">
                            <div class="activity-title">No activity yet</div>
                            <div class="activity-desc">Start the bot to see activity</div>
                        </div>
                    </li>
                `;
                return;
            }
            
            data.activities.slice(0, 10).forEach(activity => {
                const item = document.createElement('li');
                item.className = 'activity-item';
                
                const iconMap = {
                    success: '✓',
                    error: '✗',
                    warning: '⚠',
                    info: 'ℹ'
                };
                
                item.innerHTML = `
                    <div class="activity-icon ${activity.type}">${iconMap[activity.type] || 'ℹ'}</div>
                    <div class="activity-content">
                        <div class="activity-title">${escapeHtml(activity.title)}</div>
                        <div class="activity-desc">${escapeHtml(activity.description || '')}</div>
                    </div>
                    <div class="activity-time">${escapeHtml(activity.time)}</div>
                `;
                activityList.appendChild(item);
            });
        }
    } catch (error) {
        console.error('Failed to load activity log:', error);
    }
}

// ============ CONSOLE LOG ============
async function loadConsoleLog() {
    try {
        const data = await apiCall('/api/logs');
        const consoleOutput = document.getElementById('console-output');
        
        if (consoleOutput && data.logs) {
            consoleOutput.innerHTML = '';
            
            if (data.logs.length === 0) {
                consoleOutput.innerHTML = '<div class="console-line"><span class="console-message" style="color: var(--muted);">No logs yet</span></div>';
                return;
            }
            
            data.logs.slice(-50).forEach(log => {
                const line = document.createElement('div');
                line.className = 'console-line';
                line.innerHTML = `
                    <span class="console-timestamp">[${escapeHtml(log.timestamp)}]</span>
                    <span class="console-level ${log.level}">${log.level.toUpperCase()}</span>
                    <span class="console-message">${escapeHtml(log.message)}</span>
                `;
                consoleOutput.appendChild(line);
            });
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
    } catch (error) {
        console.error('Failed to load console log:', error);
    }
}

// ============ SESSION HISTORY ============
async function loadSessionHistory() {
    try {
        const data = await apiCall('/api/sessions');
        const tbody = document.querySelector('#tab-sessions tbody');
        
        if (tbody && data.sessions) {
            tbody.innerHTML = '';
            
            if (data.sessions.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" style="text-align: center; color: var(--muted); padding: var(--space-xl);">
                            No session history yet
                        </td>
                    </tr>
                `;
                return;
            }
            
            data.sessions.forEach(session => {
                const statusClass = session.status === 'SUCCESS' ? 'success' : 
                                   session.status === 'PARTIAL' ? 'warning' : 'danger';
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span style="font-family: var(--font-mono); font-size: 13px;">${escapeHtml(session.id)}</span></td>
                    <td>${escapeHtml(session.date)}</td>
                    <td>${escapeHtml(session.duration)}</td>
                    <td><span style="font-weight: 700;">${session.attempts}</span></td>
                    <td><span style="font-weight: 700;">${escapeHtml(session.courses)}</span></td>
                    <td><span style="font-weight: 700;">${session.sks}</span></td>
                    <td><span class="badge badge-${statusClass}">${escapeHtml(session.status)}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline" style="padding: 6px 12px;">VIEW</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load session history:', error);
    }
}

// ============ COURSE MANAGEMENT ============
async function addCourse() {
    const code = document.getElementById('course-code')?.value?.trim();
    const name = document.getElementById('course-name')?.value?.trim();
    const sks = parseInt(document.getElementById('course-sks')?.value) || 3;
    const className = document.getElementById('course-class')?.value || 'A';
    const schedule = document.getElementById('course-schedule')?.value?.trim();
    const type = document.getElementById('course-type')?.value || 'Wajib';
    const isFallback = document.getElementById('course-fallback')?.checked || false;
    
    // Validation
    if (!code) {
        showToast('Course code is required', 'error');
        return;
    }
    if (!name) {
        showToast('Course name is required', 'error');
        return;
    }
    if (!schedule) {
        showToast('Schedule is required', 'error');
        return;
    }
    
    const course = {
        code: code,
        name: name,
        sks: sks,
        class_name: className,
        schedule: schedule,
        type: type,
        is_fallback: isFallback
    };
    
    try {
        const data = await apiCall('/api/courses', {
            method: 'POST',
            body: JSON.stringify(course)
        });
        
        if (data.success) {
            showToast('Course added successfully', 'success');
            closeModal();
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(data.error || 'Failed to add course');
        }
    } catch (error) {
        showToast('Failed to add course: ' + error.message, 'error');
    }
}

async function deleteCourse(courseId) {
    if (!confirm('Are you sure you want to delete this course?')) return;
    
    try {
        const data = await apiCall(`/api/courses/${courseId}`, {
            method: 'DELETE'
        });
        
        if (data.success) {
            showToast('Course deleted successfully', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(data.error || 'Failed to delete course');
        }
    } catch (error) {
        showToast('Failed to delete course: ' + error.message, 'error');
    }
}

// ============ EXPORT FUNCTIONS ============
function exportCourses() {
    showToast('Exporting courses...', 'info');
    window.location.href = '/api/courses/export';
}

function exportCSV() {
    showToast('Exporting data to CSV...', 'info');
    window.location.href = '/api/export/csv';
}

function exportJSON() {
    showToast('Exporting data to JSON...', 'info');
    window.location.href = '/api/export/json';
}

// ============ MODAL MANAGEMENT ============
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId || 'modal-add-course');
    if (modal) {
        modal.classList.remove('active');
        // Reset form
        const inputs = modal.querySelectorAll('input[type="text"], input[type="number"]');
        inputs.forEach(input => input.value = '');
        const checkboxes = modal.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = false);
    }
}

// ============ TAB SWITCHING ============
function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            
            // Update active tab
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
                content.style.display = 'none';
            });
            
            const targetContent = document.getElementById('tab-' + tabName);
            if (targetContent) {
                targetContent.classList.add('active');
                targetContent.style.display = 'block';
            }
        });
    });
}

// ============ HAMBURGER MENU ============
function initHamburgerMenu() {
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', function() {
            this.classList.toggle('active');
            mobileMenu.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
                hamburger.classList.remove('active');
                mobileMenu.classList.remove('active');
            }
        });
    }
}

// ============ INITIALIZATION ============
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tabs
    initTabs();
    
    // Initialize hamburger menu
    initHamburgerMenu();
    
    // Setup bot control buttons
    const btnStart = document.getElementById('btn-start');
    if (btnStart) btnStart.addEventListener('click', startBot);
    
    const btnStop = document.getElementById('btn-stop');
    if (btnStop) btnStop.addEventListener('click', stopBot);
    
    const btnDryRun = document.getElementById('btn-dry-run');
    if (btnDryRun) btnDryRun.addEventListener('click', dryRun);
    
    const btnCheckStatus = document.getElementById('btn-status');
    if (btnCheckStatus) btnCheckStatus.addEventListener('click', checkStatus);
    
    // Setup course management buttons
    const btnAddCourse = document.getElementById('btn-add-mk');
    if (btnAddCourse) {
        btnAddCourse.addEventListener('click', () => openModal('modal-add-course'));
    }
    
    const btnExportCourses = document.getElementById('btn-export');
    if (btnExportCourses && document.getElementById('priority-table')) {
        btnExportCourses.addEventListener('click', exportCourses);
    }
    
    // Setup modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal-overlay').classList.remove('active');
        });
    });
    
    // Close modal on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(modal => {
                modal.classList.remove('active');
            });
        }
    });
    
    // Load initial data
    loadActivityLog();
    
    // Load session history if on riwayat page
    if (document.getElementById('tab-sessions')) {
        loadSessionHistory();
    }
    
    // Start auto-refresh
    setInterval(updateBotStatus, 2000);
    setInterval(loadActivityLog, 5000);
    
    // Initial status update
    updateBotStatus();
});
