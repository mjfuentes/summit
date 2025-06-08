// Developer Tools JavaScript

// Auto-refresh status every 30 seconds
setInterval(async () => {
    try {
        const response = await fetch('/api/summit/status');
        const status = await response.json();
        updateStatus(status);
    } catch (error) {
        updateStatus('Connection error');
    }
}, 30000);

function updateStatus(status) {
    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.textContent = status;
    }
}

// Add click handlers for buttons
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.textContent.trim();
            handleAction(action);
        });
    });
});

function handleAction(action) {
    // Handle different actions
    switch(action) {
        case 'Create New Task':
            handleCreateTask();
            break;
        case 'View All Tasks':
            handleViewTasks();
            break;
        case 'System Logs':
            handleSystemLogs();
            break;
        case 'Performance Metrics':
            handlePerformanceMetrics();
            break;
        case 'restart':
            updateStatus('Restarting system...');
            break;
        case 'logs':
            updateStatus('Fetching logs...');
            break;
        case 'debug':
            updateStatus('Debug mode activated');
            break;
        default:
            updateStatus('Unknown action');
    }
}

function handleCreateTask() {
    // Placeholder for task creation
    alert('Task creation interface would open here');
}

function handleViewTasks() {
    // Placeholder for viewing all tasks
    alert('All tasks view would open here');
}

function handleSystemLogs() {
    // Placeholder for system logs
    alert('System logs would open here');
}

function handlePerformanceMetrics() {
    // Placeholder for performance metrics
    alert('Performance metrics would open here');
} 