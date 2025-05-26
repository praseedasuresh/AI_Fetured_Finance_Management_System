/**
 * AI Assistant JavaScript functionality
 * Enhances the chatbot with voice input, quick suggestions, and other features
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const chatMessages = document.getElementById('chatMessages');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const typingIndicator = document.getElementById('typingIndicator');
    const voiceButton = document.getElementById('voiceButton');
    const suggestionContainer = document.getElementById('suggestionContainer');
    
    // Check if we're on a chat page
    if (!chatMessages || !chatForm) return;
    
    // Get session ID from the data attribute
    const sessionId = chatMessages.dataset.sessionId;
    
    // Scroll to bottom of chat
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Process markdown in assistant messages
    function processMarkdown() {
        document.querySelectorAll('.markdown-content').forEach(function(element) {
            if (window.marked) {
                element.innerHTML = marked.parse(element.textContent);
            }
        });
    }
    
    // Initialize
    scrollToBottom();
    processMarkdown();
    
    // Quick suggestions
    const suggestions = [
        "What's our total budget this year?",
        "Show me recent expenses",
        "How much have we collected in fees?",
        "Compare department budgets"
    ];
    
    // Add suggestion chips
    if (suggestionContainer) {
        suggestions.forEach(suggestion => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip btn btn-sm btn-outline-primary me-2 mb-2';
            chip.textContent = suggestion;
            chip.addEventListener('click', function() {
                messageInput.value = suggestion;
                chatForm.dispatchEvent(new Event('submit'));
            });
            suggestionContainer.appendChild(chip);
        });
    }
    
    // Voice input functionality
    if (voiceButton && 'webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        let isListening = false;
        
        voiceButton.addEventListener('click', function() {
            if (isListening) {
                recognition.stop();
                voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
                voiceButton.classList.remove('btn-danger');
                voiceButton.classList.add('btn-outline-secondary');
            } else {
                recognition.start();
                voiceButton.innerHTML = '<i class="fas fa-stop"></i>';
                voiceButton.classList.remove('btn-outline-secondary');
                voiceButton.classList.add('btn-danger');
            }
            isListening = !isListening;
        });
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            messageInput.value = transcript;
            voiceButton.click(); // Stop recording
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            voiceButton.click(); // Stop recording
        };
    } else if (voiceButton) {
        voiceButton.style.display = 'none'; // Hide if not supported
    }
    
    // Handle form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Clear input
        messageInput.value = '';
        
        // Add user message to chat
        const userMessageElement = document.createElement('div');
        userMessageElement.className = 'message message-user';
        userMessageElement.innerHTML = `
            ${message}
            <div class="text-muted small mt-1 text-end">
                ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
            </div>
        `;
        chatMessages.appendChild(userMessageElement);
        scrollToBottom();
        
        // Show typing indicator
        typingIndicator.style.display = 'block';
        scrollToBottom();
        
        // Send message to server
        fetch(`/ai_assistant/api/chat/${sessionId}/message/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            // Add assistant message to chat
            const assistantMessageElement = document.createElement('div');
            assistantMessageElement.className = 'message message-assistant';
            assistantMessageElement.innerHTML = `
                <div class="markdown-content">${data.content}</div>
                <div class="text-muted small mt-1 text-end">
                    ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </div>
            `;
            chatMessages.appendChild(assistantMessageElement);
            
            // Process markdown in the new message
            processMarkdown();
            scrollToBottom();
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            // Add error message
            const errorMessageElement = document.createElement('div');
            errorMessageElement.className = 'message message-system';
            errorMessageElement.textContent = 'Sorry, there was an error processing your request. Please try again.';
            chatMessages.appendChild(errorMessageElement);
            scrollToBottom();
        });
    });
});
