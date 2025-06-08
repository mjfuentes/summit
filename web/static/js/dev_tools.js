/**
 * Summit AI Developer Dashboard
 * Real-time dashboard with charts, agent monitoring, and system statistics
 */

// Global state
let charts = {};
let autoRefreshInterval;
let isLoading = false;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', async function() {
    initializeDashboard();
});

async function initializeDashboard() {
    showLoading(true);
    
    try {
        // Load initial data
        await Promise.all([
            loadSystemStatistics(),
            loadAgentData(),
            loadActivityData(),
            loadChartData()
        ]);
        
        // Setup auto-refresh
        setupAutoRefresh();
        
        // Update last refresh time
        updateLastRefreshTime();
        
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        showError('Failed to load dashboard data');
    } finally {
        showLoading(false);
    }
}

// Auto-refresh functionality
function setupAutoRefresh() {
    const autoRefreshToggle = document.getElementById('autoRefresh');
    
    autoRefreshToggle.addEventListener('change', function() {
        if (this.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
    
    // Start auto-refresh by default
    if (autoRefreshToggle.checked) {
        startAutoRefresh();
    }
}

function startAutoRefresh() {
    stopAutoRefresh(); // Clear any existing interval
    autoRefreshInterval = setInterval(async () => {
        if (!isLoading) {
            await refreshAllData();
        }
    }, 30000); // 30 seconds
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Load system statistics
async function loadSystemStatistics() {
    try {
        const response = await fetch('/api/system/statistics');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            updateSystemHealth(data.system_health);
            updateTaskStatistics(data.task_statistics);
            updateAgentSummary(data.agent_statistics);
            
            // Update system status badge
            const systemStatus = document.getElementById('systemStatus');
            systemStatus.className = 'badge operational';
            systemStatus.querySelector('span').textContent = 'System Operational';
        } else {
            throw new Error(data.message || 'Unknown error');
        }
    } catch (error) {
        console.error('Failed to load system statistics:', error);
        updateSystemStatusError();
        
        // Show error state in components
        updateSystemHealth({
            database: { status: 'error' },
            agents: { status: 'error', count: 0 },
            task_queue: { status: 'error', pending_count: 0 }
        });
        updateTaskStatistics({
            total_tasks: 0,
            active_tasks: 0,
            completed_tasks: 0,
            success_rate_percent: 0
        });
        updateAgentSummary({
            total_agents: 0,
            active_agents: 0,
            roles_distribution: { product: 0, engineering: 0, quality_control: 0 }
        });
    }
}

function updateSystemHealth(healthData) {
    const dbStatus = document.getElementById('dbStatus');
    const agentsStatus = document.getElementById('agentsStatus');
    const queueStatus = document.getElementById('queueStatus');
    
    // Database status
    dbStatus.textContent = healthData.database?.status || 'Unknown';
    dbStatus.className = `health-status ${healthData.database?.status || 'unknown'}`;
    
    // Agents status
    const agentCount = healthData.agents?.count || 0;
    agentsStatus.textContent = agentCount > 0 ? 
        `${healthData.agents.status} (${agentCount})` : 
        'No agents registered';
    agentsStatus.className = `health-status ${healthData.agents?.status || 'unknown'}`;
    
    // Queue status
    const pendingCount = healthData.task_queue?.pending_count || 0;
    queueStatus.textContent = `${healthData.task_queue?.status || 'Unknown'} (${pendingCount} pending)`;
    queueStatus.className = `health-status ${healthData.task_queue?.status || 'unknown'}`;
}

function updateTaskStatistics(taskStats) {
    const totalTasks = taskStats.total_tasks || 0;
    const activeTasks = taskStats.active_tasks || 0;
    const completedTasks = taskStats.completed_tasks || 0;
    const successRate = taskStats.success_rate_percent || 0;
    
    // Update numbers with empty state classes
    const totalElement = document.getElementById('totalTasks');
    totalElement.textContent = totalTasks;
    totalElement.className = totalTasks === 0 ? 'stat-number empty' : 'stat-number';
    
    const activeElement = document.getElementById('activeTasks');
    activeElement.textContent = activeTasks;
    activeElement.className = activeTasks === 0 ? 'stat-number empty' : 'stat-number';
    
    const completedElement = document.getElementById('completedTasks');
    completedElement.textContent = completedTasks;
    completedElement.className = completedTasks === 0 ? 'stat-number empty' : 'stat-number';
    
    const successElement = document.getElementById('successRate');
    successElement.textContent = `${successRate}%`;
    successElement.className = successRate === 0 ? 'stat-number empty' : 'stat-number';
}

function updateAgentSummary(agentStats) {
    const totalAgents = agentStats.total_agents || 0;
    const activeAgents = agentStats.active_agents || 0;
    const productCount = agentStats.roles_distribution?.product || 0;
    const engineeringCount = agentStats.roles_distribution?.engineering || 0;
    const qualityCount = agentStats.roles_distribution?.quality_control || 0;
    
    const agentSummaryElement = document.getElementById('agentSummary');
    
    if (totalAgents === 0) {
        // Show empty state for agent summary
        agentSummaryElement.className = 'agent-summary empty';
        agentSummaryElement.innerHTML = `
            <i class="fas fa-robot"></i>
            <div class="empty-title">No Agents Registered</div>
            <div class="empty-subtitle">Agents will appear here once they're deployed and registered with the system.</div>
        `;
    } else {
        agentSummaryElement.className = 'agent-summary';
        agentSummaryElement.innerHTML = `
            <div class="agent-roles">
                <div class="role-item ${productCount === 0 ? 'disabled' : ''}">
                    <div class="role-icon product"><i class="fas fa-lightbulb"></i></div>
                    <div class="role-info">
                        <span class="role-name">Product</span>
                        <span class="role-count ${productCount === 0 ? 'zero' : ''}">${productCount}</span>
                    </div>
                </div>
                <div class="role-item ${engineeringCount === 0 ? 'disabled' : ''}">
                    <div class="role-icon engineering"><i class="fas fa-code"></i></div>
                    <div class="role-info">
                        <span class="role-name">Engineering</span>
                        <span class="role-count ${engineeringCount === 0 ? 'zero' : ''}">${engineeringCount}</span>
                    </div>
                </div>
                <div class="role-item ${qualityCount === 0 ? 'disabled' : ''}">
                    <div class="role-icon quality"><i class="fas fa-check-circle"></i></div>
                    <div class="role-info">
                        <span class="role-name">Quality Control</span>
                        <span class="role-count ${qualityCount === 0 ? 'zero' : ''}">${qualityCount}</span>
                    </div>
                </div>
            </div>
            <div class="agent-status-summary">
                ${totalAgents} total agent${totalAgents !== 1 ? 's' : ''}, 
                ${activeAgents} active
            </div>
        `;
    }
}

// Load agent data
async function loadAgentData() {
    try {
        const response = await fetch('/api/agents/status');
        const data = await response.json();
        
        if (data.success) {
            updateAgentTable(data.agents);
        }
    } catch (error) {
        console.error('Failed to load agent data:', error);
    }
}

function updateAgentTable(agents) {
    const tableBody = document.getElementById('agentTableBody');
    tableBody.innerHTML = '';
    
    if (agents.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="no-data">
                    <i class="fas fa-robot"></i>
                    <div class="empty-title">No Agents Available</div>
                    <div class="empty-subtitle">Deploy agents to start seeing monitoring data here</div>
                </td>
            </tr>
        `;
        return;
    }
    
    agents.forEach(agent => {
        const row = document.createElement('tr');
        const totalTasks = agent.completed_tasks + agent.failed_tasks;
        const successRate = totalTasks > 0 ? ((agent.completed_tasks / totalTasks) * 100).toFixed(1) : 0;
        
        row.innerHTML = `
            <td><code>${agent.id.substring(0, 8)}...</code></td>
            <td><span class="role-badge ${agent.role}">${agent.role}</span></td>
            <td><span class="status-badge ${agent.status || 'unknown'}">${agent.status || 'Unknown'}</span></td>
            <td>${agent.completed_tasks || 0}</td>
            <td>${successRate}%</td>
            <td>${formatUptime(agent.uptime_hours || 0)}</td>
            <td>${formatTimestamp(agent.last_heartbeat)}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Load activity data
async function loadActivityData() {
    try {
        const response = await fetch('/api/system/activity');
        const data = await response.json();
        
        if (data.success) {
            updateActivityFeed(data.activity);
        }
    } catch (error) {
        console.error('Failed to load activity data:', error);
    }
}

function updateActivityFeed(activities) {
    const activityFeed = document.getElementById('activityFeed');
    activityFeed.innerHTML = '';
    
    if (activities.length === 0) {
        activityFeed.innerHTML = `
            <div class="no-activity">
                <i class="fas fa-history"></i>
                <div class="empty-title">No Recent Activity</div>
                <div class="empty-subtitle">Activity will appear here as tasks are created and completed</div>
            </div>
        `;
        return;
    }
    
    activities.forEach(activity => {
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        
        const statusIcon = getStatusIcon(activity.status);
        const duration = activity.duration_minutes ? `(${activity.duration_minutes}m)` : '';
        
        activityItem.innerHTML = `
            <div class="activity-icon ${activity.status}">
                <i class="fas ${statusIcon}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${activity.title}</div>
                <div class="activity-meta">
                    <span class="activity-role">${activity.agent_role}</span>
                    <span class="activity-time">${formatTimestamp(activity.timestamp)}</span>
                    ${duration}
                </div>
            </div>
            <div class="activity-status ${activity.status}">${activity.status}</div>
        `;
        
        activityFeed.appendChild(activityItem);
    });
}

// Load chart data
async function loadChartData() {
    try {
        const [timelineResponse, performanceResponse] = await Promise.all([
            fetch('/api/charts/task-timeline'),
            fetch('/api/charts/agent-performance')
        ]);
        
        const timelineData = await timelineResponse.json();
        const performanceData = await performanceResponse.json();
        
        if (timelineData.success) {
            updateTaskTimelineChart(timelineData.timeline);
        }
        
        if (performanceData.success) {
            updateTaskStatusChart(performanceData.agent_performance);
        }
    } catch (error) {
        console.error('Failed to load chart data:', error);
    }
}

function updateTaskTimelineChart(timelineData) {
    const chartContainer = document.getElementById('taskTimelineChart').parentElement;
    const ctx = document.getElementById('taskTimelineChart').getContext('2d');
    
    // Check if we have meaningful data
    const hasData = timelineData && timelineData.length > 0 && 
                   timelineData.some(d => d.total > 0);
    
    if (!hasData) {
        // Show empty state
        chartContainer.className = 'chart-container empty';
        chartContainer.innerHTML = `
            <i class="fas fa-chart-line"></i>
            <div class="empty-chart-title">No Task Data</div>
            <div class="empty-chart-subtitle">Task timeline will appear here once you start creating tasks</div>
        `;
        return;
    }
    
    // Restore normal chart container
    chartContainer.className = 'chart-container';
    chartContainer.innerHTML = '<canvas id="taskTimelineChart"></canvas>';
    
    if (charts.timeline) {
        charts.timeline.destroy();
    }
    
    const newCtx = document.getElementById('taskTimelineChart').getContext('2d');
    charts.timeline = new Chart(newCtx, {
        type: 'line',
        data: {
            labels: timelineData.map(d => d.day_name),
            datasets: [
                {
                    label: 'Completed',
                    data: timelineData.map(d => d.completed),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true
                },
                {
                    label: 'Failed',
                    data: timelineData.map(d => d.failed),
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    fill: true
                },
                {
                    label: 'Pending',
                    data: timelineData.map(d => d.pending),
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                }
            }
        }
    });
}

function updateTaskStatusChart(performanceData) {
    const chartContainer = document.getElementById('taskStatusChart').parentElement;
    const ctx = document.getElementById('taskStatusChart').getContext('2d');
    
    // Calculate totals for pie chart
    const totals = performanceData.reduce((acc, agent) => {
        acc.completed += agent.completed_tasks || 0;
        acc.failed += agent.failed_tasks || 0;
        return acc;
    }, { completed: 0, failed: 0 });
    
    const hasData = totals.completed > 0 || totals.failed > 0;
    
    if (!hasData) {
        // Show empty state
        chartContainer.className = 'chart-container empty';
        chartContainer.innerHTML = `
            <i class="fas fa-pie-chart"></i>
            <div class="empty-chart-title">No Task Distribution Data</div>
            <div class="empty-chart-subtitle">Task completion statistics will appear here as agents complete tasks</div>
        `;
        return;
    }
    
    // Restore normal chart container
    chartContainer.className = 'chart-container';
    chartContainer.innerHTML = '<canvas id="taskStatusChart"></canvas>';
    
    if (charts.status) {
        charts.status.destroy();
    }
    
    const newCtx = document.getElementById('taskStatusChart').getContext('2d');
    charts.status = new Chart(newCtx, {
        type: 'doughnut',
        data: {
            labels: ['Completed', 'Failed'],
            datasets: [{
                data: [totals.completed, totals.failed],
                backgroundColor: ['#10b981', '#ef4444'],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Utility functions
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
}

function formatUptime(hours) {
    if (hours < 1) return `${Math.floor(hours * 60)}m`;
    if (hours < 24) return `${Math.floor(hours)}h`;
    return `${Math.floor(hours / 24)}d`;
}

function getStatusIcon(status) {
    const icons = {
        'completed': 'fa-check-circle',
        'failed': 'fa-times-circle',
        'running': 'fa-play-circle',
        'pending': 'fa-clock',
        'stopped': 'fa-stop-circle'
    };
    return icons[status] || 'fa-question-circle';
}

function updateLastRefreshTime() {
    const lastUpdate = document.getElementById('lastUpdate');
    lastUpdate.querySelector('span').textContent = `Last Updated: ${new Date().toLocaleTimeString()}`;
}

function showLoading(show) {
    isLoading = show;
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
    
    if (show) {
        // Add loading classes to elements
        document.querySelectorAll('.stat-number').forEach(el => {
            el.classList.add('loading');
        });
        document.querySelectorAll('.health-status').forEach(el => {
            el.classList.add('loading');
        });
        document.querySelectorAll('.role-count').forEach(el => {
            el.classList.add('loading');
        });
    } else {
        // Remove loading classes
        document.querySelectorAll('.stat-number').forEach(el => {
            el.classList.remove('loading');
        });
        document.querySelectorAll('.health-status').forEach(el => {
            el.classList.remove('loading');
        });
        document.querySelectorAll('.role-count').forEach(el => {
            el.classList.remove('loading');
        });
    }
}

function showError(message) {
    // You could implement a toast notification here
    console.error(message);
}

function updateSystemStatusError() {
    const systemStatus = document.getElementById('systemStatus');
    systemStatus.className = 'badge error';
    systemStatus.querySelector('span').textContent = 'System Error';
    
    // Update health statuses to error state
    document.getElementById('dbStatus').className = 'health-status error';
    document.getElementById('agentsStatus').className = 'health-status error';
    document.getElementById('queueStatus').className = 'health-status error';
}

// Action button handlers
async function createNewTask() {
    window.location.href = '/';
}

async function viewAllTasks() {
    // Open tasks in a new window/tab or modal
    window.open('/api/tasks', '_blank');
}

async function viewSystemLogs() {
    alert('System logs viewer not implemented yet');
}

async function exportData() {
    try {
        const data = await Promise.all([
            fetch('/api/system/statistics').then(r => r.json()),
            fetch('/api/agents/status').then(r => r.json()),
            fetch('/api/system/activity').then(r => r.json())
        ]);
        
        const exportData = {
            timestamp: new Date().toISOString(),
            system_statistics: data[0],
            agents: data[1],
            activity: data[2]
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `summit-dashboard-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('Failed to export data: ' + error.message);
    }
}

async function retriggerFailedTasks() {
    if (!confirm('Are you sure you want to retrigger all failed tasks?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/tasks/retrigger-all-failed', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            alert(`Successfully retriggered ${data.retriggered_count} tasks`);
            await refreshAllData();
        } else {
            alert('Failed to retrigger tasks: ' + data.message);
        }
    } catch (error) {
        alert('Failed to retrigger tasks: ' + error.message);
    }
}

async function cleanupOldTasks() {
    if (!confirm('Are you sure you want to cleanup old tasks? This will remove tasks older than 7 days.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/tasks/cleanup', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            alert(`Successfully cleaned up ${data.deleted_count} old tasks`);
            await refreshAllData();
        } else {
            alert('Failed to cleanup tasks: ' + data.message);
        }
    } catch (error) {
        alert('Failed to cleanup tasks: ' + error.message);
    }
}

// Individual refresh functions for manual refresh buttons
async function refreshAgentData() {
    await loadAgentData();
}

async function refreshActivityData() {
    await loadActivityData();
}

// Refresh all data
async function refreshAllData() {
    try {
        await Promise.all([
            loadSystemStatistics(),
            loadAgentData(),
            loadActivityData(),
            loadChartData()
        ]);
        updateLastRefreshTime();
    } catch (error) {
        console.error('Failed to refresh data:', error);
    }
} 