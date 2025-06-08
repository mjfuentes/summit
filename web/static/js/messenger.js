const chatArea = document.getElementById('chatArea');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

function addMessage(content, sender, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'summit'}`;
    
    const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    messageDiv.innerHTML = `
        <div class="message-sender">${sender}</div>
        <div class="message-bubble">${content}</div>
        <div class="message-time">${time}</div>
    `;
    
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping() {
    typingIndicator.style.display = 'block';
    chatArea.scrollTop = chatArea.scrollHeight;
}

function hideTyping() {
    typingIndicator.style.display = 'none';
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Add user message
    addMessage(message, 'You', true);
    messageInput.value = '';
    sendBtn.disabled = true;
    
    // Show typing indicator
    showTyping();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        // Hide typing indicator and create Summit's message container
        hideTyping();
        
        // Create Summit's message div for streaming
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message summit';
        
        const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        messageDiv.innerHTML = `
            <div class="message-sender">Summit</div>
            <div class="message-bubble" id="streaming-response"></div>
            <div class="message-time">${time}</div>
        `;
        
        chatArea.appendChild(messageDiv);
        chatArea.scrollTop = chatArea.scrollHeight;
        
        const streamingBubble = document.getElementById('streaming-response');
        let fullResponse = '';
        
        // Add typing cursor while streaming
        streamingBubble.classList.add('typing-cursor');
        
        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'content') {
                            fullResponse += data.content;
                            
                            // Check if we just completed a sentence (ends with . ! ? or double newline)
                            const sentenceEnders = /[.!?]\s*$|(\n\n)$/;
                            const justCompletedSentence = sentenceEnders.test(data.content);
                            
                            // Convert newlines to <br> and update the bubble
                            streamingBubble.innerHTML = fullResponse.replace(/\n/g, '<br>');
                            chatArea.scrollTop = chatArea.scrollHeight;
                            
                            if (justCompletedSentence) {
                                // Long pause between sentences (3-8 seconds for testing, can be increased)
                                const pauseTime = 3000 + Math.random() * 5000; // 3-8 seconds
                                
                                // Show "Summit is thinking..." during long pauses
                                const originalContent = streamingBubble.innerHTML;
                                streamingBubble.innerHTML = originalContent + '<br><em style="color: #666; font-size: 10px; animation: pulse 1s infinite;">Summit is thinking...</em>';
                                
                                await new Promise(resolve => setTimeout(resolve, pauseTime));
                                
                                // Remove the thinking indicator
                                streamingBubble.innerHTML = originalContent;
                            } else {
                                // Fast typing within sentences (very short delay)
                                await new Promise(resolve => setTimeout(resolve, 5));
                            }
                        } else if (data.type === 'done') {
                            // Check if response contains task creation
                            if (fullResponse.includes('Task ID:')) {
                                streamingBubble.innerHTML = enhanceTaskMessage(fullResponse.replace(/\n/g, '<br>'));
                            }
                            break;
                        }
                    } catch (e) {
                        // Ignore JSON parse errors for malformed chunks
                    }
                }
            }
        }
        
        // Remove the typing cursor and ID since we're done streaming
        streamingBubble.classList.remove('typing-cursor');
        streamingBubble.removeAttribute('id');
        
        sendBtn.disabled = false;
        messageInput.focus();
        
    } catch (error) {
        hideTyping();
        addMessage('Sorry, I encountered an error. Please try again.', 'Summit');
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function enhanceTaskMessage(responseText) {
    // Extract task ID from the response
    const taskIdMatch = responseText.match(/Task ID: ([a-f0-9-]+)\.\.\./);
    if (taskIdMatch) {
        const taskId = taskIdMatch[1];
        const taskLink = `<br><br><div style="background: #f0f0f0; padding: 8px; border: 1px inset #ece9d8; margin-top: 8px;">
            <strong>Task Management:</strong><br>
            <a href="#" onclick="showTaskDetails('${taskId}')" style="color: #000080; text-decoration: underline;">View Task Details</a> | 
            <a href="#" onclick="refreshTaskStatus('${taskId}')" style="color: #000080; text-decoration: underline;">Refresh Status</a>
        </div>`;
        
        return responseText + taskLink;
    }
    return responseText;
}

async function showTaskDetails(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const data = await response.json();
        
        if (data.success) {
            const task = data.task;
            const details = `
                <strong>Task Details:</strong><br>
                ID: ${task.task_id}<br>
                Status: ${task.status}<br>
                Progress: ${task.progress || 'No progress yet'}<br>
                Created: ${new Date(task.created_at).toLocaleString()}<br>
                Description: ${task.task_description}
            `;
            addMessage(details, 'System');
        } else {
            addMessage('Could not fetch task details.', 'System');
        }
    } catch (error) {
        addMessage('Error fetching task details.', 'System');
    }
}

async function refreshTaskStatus(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const data = await response.json();
        
        if (data.success) {
            const task = data.task;
            const status = `Task ${taskId.substring(0, 8)}... Status: ${task.status} - ${task.progress || 'No progress update'}`;
            addMessage(status, 'System');
        } else {
            addMessage('Could not refresh task status.', 'System');
        }
    } catch (error) {
        addMessage('Error refreshing task status.', 'System');
    }
}

// Focus input on load
messageInput.focus(); 