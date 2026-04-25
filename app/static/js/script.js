document.addEventListener("DOMContentLoaded", () => {
  // --- UI ELEMENT SELECTORS ---
  const chatForm = document.getElementById("chat-form");
  const sendButton = document.getElementById("send-button");
  const newChatButton = document.querySelector(".new-chat-button");
  const chatMessages = document.getElementById("chat-messages");
  const messageInput = document.getElementById("message-input");
  const imageInput = document.getElementById("image-input");
  const imageInputLabel = document.querySelector(".image-input-label");
  const imagePreviewContainer = document.getElementById(
    "image-preview-container"
  );
  const userIdInput = document.getElementById("user-id");
  const deviceNumberInput = document.getElementById("device-number");
  const sessionIdInput = document.getElementById("session-id");
  const chatList = document.querySelector(".chat-list");
  const deviceConnectionToggle = document.getElementById('device-connection-toggle');



  // --- STATE MANAGEMENT ---
  let currentImageFile = null;
  let loadingIndicatorElement = null;
  const sendIcon = sendButton.innerHTML;
  const thinkingIcon = `<div class="loader"></div>`;
  // Timer for loading indicator
  let loadingTimerInterval = null;
  let elapsedSeconds = 0;

  // --- API & CORE FUNCTIONS ---

  function generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Date.now() + Math.random() * 16) % 16 | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function ensureUserId() {
    if (!userIdInput.value.trim()) {
      const randomId = "demo-ui-" + Math.random().toString(36).substring(2, 7);
      userIdInput.value = randomId;
    }
  }

  function escapeHtml(unsafe) {
    if (unsafe === null || typeof unsafe === "undefined") return "";
    return unsafe.toString().replace(
      /[&<>"']/g,
      (m) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      }[m])
    );
  }

  function createRecipeCardHtml(recipe, sourceText = '') {
    const sourceTag = sourceText ? ` <span class="source-tag">${escapeHtml(sourceText)}</span>` : '';
    let content = `<details class="recipe-card"><summary><strong>${escapeHtml(recipe.name)}</strong>${sourceTag}</summary>`;
    if (recipe.description) content += `<p><em>${escapeHtml(recipe.description)}</em></p>`;
    let meta = [];
    
    // Handle both nested glassware object and flat glassware_type field
    const glasswareType = recipe.glassware?.type || recipe.glassware_type;
    if (glasswareType) meta.push(`<strong>Glass:</strong> ${escapeHtml(glasswareType)}`);
    
    if (recipe.mixingTechnique) meta.push(`<strong>Mixing:</strong> ${escapeHtml(recipe.mixingTechnique)}`);
    if (recipe.difficulty) meta.push(`<strong>Difficulty:</strong> ${escapeHtml(recipe.difficulty)}`);
    if (meta.length > 0) content += `<div class="recipe-meta">${meta.join(' &middot; ')}</div>`;
    
    content += '<h5>Ingredients:</h5><ul>';
    
    // Check if recipe is in flat format (has no_ingredients field)
    if (typeof recipe.no_ingredients === 'number') {
      // Flat recipe format: extract ingredients from indexed fields
      for (let i = 0; i < recipe.no_ingredients; i++) {
        const ingredientName = recipe[`ingredient_${i}`];
        const quantity = recipe[`quantity_${i}`];
        
        if (ingredientName) {
          // quantity_N is already a string like "2 oz", so use it directly
          const displayText = quantity ? `${quantity} ${ingredientName}` : ingredientName;
          content += `<li>${escapeHtml(displayText)}</li>`;
        }
      }
    } else if (recipe.ingredients && Array.isArray(recipe.ingredients)) {
      // Nested recipe format: use ingredients array
      recipe.ingredients.forEach(ing => {
        content += `<li>${escapeHtml(`${ing.quantity || ''} ${ing.unit || ''} ${ing.name || ''}`.trim())}</li>`;
      });
    }
    
    content += '</ul>';
    
    // Only show instructions if they exist
    if (recipe.instructions && recipe.instructions.length > 0) {
      content += '<h5>Instructions:</h5><ol>';
      recipe.instructions.forEach(inst => content += `<li>${escapeHtml(inst)}</li>`);
      content += '</ol>';
    }
    
    content += '</details>';
    return content;
  }

  function createMixlistCardHtml(mixlist) {
    let content = `<details class="mixlist-card"><summary><strong>${escapeHtml(mixlist.name)}</strong> <span class="source-tag">Mixlist</span></summary>`;
    if (mixlist.description) content += `<p><em>${escapeHtml(mixlist.description)}</em></p>`;
    if (mixlist.recipes && mixlist.recipes.length > 0) {
      content += '<h5>Recipes in this mixlist:</h5>';
      content += '<div class="recipe-cards-container">';
      mixlist.recipes.forEach(recipe => {
        content += createRecipeCardHtml(recipe, 'from ChatBot');
      });
      content += '</div>';
    }
    content += '</details>';
    return content;
  }

  /**
   * Parses the conversation history response from the conversation_messages table
   * into a format that the addMessageToUI function can easily render.
   */
  function parseHistoryResponse(apiResponse) {
    const messages = [];
    if (!apiResponse || !apiResponse.messages) return messages;

    // The conversation_messages table stores complete UI-ready data
    apiResponse.messages.forEach((msg) => {
      // Add user message
      if (msg.user_message && msg.user_message.trim()) {
        messages.push({
          sender: "user",
          data: { text: msg.user_message },
        });
      }

      // Add assistant message with all UI components
      if (msg.bot_message && msg.bot_message.trim()) {
        const assistantMessageData = {
          response: msg.bot_message,
        };

        // Add message_id if present (for feedback functionality)
        if (msg.id) {
          assistantMessageData.message_id = msg.id;
        }

        // Add action cards if present
        if (msg.action_cards && Array.isArray(msg.action_cards) && msg.action_cards.length > 0) {
          assistantMessageData.action_cards = msg.action_cards;
        }

        // Add AI-generated recipes if present
        if (msg.ai_generated_recipe && Array.isArray(msg.ai_generated_recipe) && msg.ai_generated_recipe.length > 0) {
          assistantMessageData.recipes = msg.ai_generated_recipe;
        }

        // Add ChatBot data if present
        const hasChatBotRecipes = msg.chatbot_recipe && Array.isArray(msg.chatbot_recipe) && msg.chatbot_recipe.length > 0;
        const hasChatBotMixlists = msg.chatbot_mixlist && Array.isArray(msg.chatbot_mixlist) && msg.chatbot_mixlist.length > 0;
        
        if (hasChatBotRecipes || hasChatBotMixlists) {
          assistantMessageData.chatbot = {};
          if (hasChatBotRecipes) {
            assistantMessageData.chatbot.recipes = msg.chatbot_recipe;
          }
          if (hasChatBotMixlists) {
            assistantMessageData.chatbot.mixlists = msg.chatbot_mixlist;
          }
        }

        messages.push({
          sender: "assistant",
          data: assistantMessageData,
        });
      }
    });

    return messages;
  }
  /**
   * Renders a message in the chat window. This function is now simplified as the
   * parsing is handled by `parseHistoryResponse`.
   */
  function addMessageToUI(sender, messageData, isError = false) {
    const messageClass = sender === "user" ? "sent" : "received";
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", messageClass);

    const contentElement = document.createElement("div");
    contentElement.classList.add("message-content");

    if (sender === 'user') {
      let userText = escapeHtml(messageData.text);
      if (messageData.imageName) { // For real-time display before sending
        userText += `<br><span class="image-name-tag">Image: ${escapeHtml(messageData.imageName)}</span>`;
      }
      contentElement.innerHTML = userText;
    } else { // Assistant
      if (isError) {
        contentElement.innerHTML = `<p class="error-message">${escapeHtml(messageData)}</p>`;
      } else {
        let content = '';
        if (messageData.response) {
          content += `<p>${escapeHtml(messageData.response).replace(/\n/g, '<br>')}</p>`;
        }

        // Relevant URL (if present)
        if (messageData.relevant_url) {
          content += `
            <div class="relevant-url-container">
              <span class="material-icons">link</span>
              <div class="relevant-url-content">
                <div class="relevant-url-label">Learn More</div>
                <a href="${escapeHtml(messageData.relevant_url)}" target="_blank" rel="noopener noreferrer" class="relevant-url-link">
                  ${escapeHtml(messageData.relevant_url)}
                  <span class="material-icons">open_in_new</span>
                </a>
              </div>
            </div>
          `;
        }

        // Agent-generated recipes
        if (messageData.recipes && messageData.recipes.length > 0) {
          content += '<h4>Suggested for you:</h4>';
          content += '<div class="recipe-cards-container">';
          messageData.recipes.forEach(recipe => {
            const sourceText = (recipe.source || '').toLowerCase() === 'chatbot' ? 'from ChatBot' : '';
            content += createRecipeCardHtml(recipe, sourceText);
          });
          content += '</div>';
        }

        // ChatBot data from DB Search
        if (messageData.chatbot && (messageData.chatbot.recipes?.length > 0 || messageData.chatbot.mixlists?.length > 0)) {

          if (messageData.chatbot.recipes && messageData.chatbot.recipes.length > 0) {
            content += '<hr class="content-divider">';
            content += '<h4>From your ChatBot Library:</h4>';
            content += '<div class="recipe-cards-container">';
            messageData.chatbot.recipes.forEach(recipe => {
              content += createRecipeCardHtml(recipe, 'from ChatBot');
            });
            content += '</div>';
          }

          if (messageData.chatbot.mixlists && messageData.chatbot.mixlists.length > 0) {
            content += '<hr class="content-divider">';
            content += '<h4>Mixlists from your ChatBot Library:</h4>';
            content += '<div class="mixlist-cards-container">';
            messageData.chatbot.mixlists.forEach(mixlist => {
              content += createMixlistCardHtml(mixlist);
            });
            content += '</div>';
          }
        }

        if (messageData.action_cards && messageData.action_cards.length > 0) {
          content += '<div class="action-cards-container">';
          messageData.action_cards.forEach(card => {
            content += `<button class="action-card ${escapeHtml(card.type)}-action" data-value="${escapeHtml(card.value)}" data-type="${escapeHtml(card.type)}" data-action-id="${escapeHtml(card.action_id)}">${escapeHtml(card.label)}</button> `;
          });
          content += '</div>';
        }
        contentElement.innerHTML = content || '<p>Received an empty response.</p>';
        
        // Add feedback buttons for assistant messages (only if message_id exists)
        if (messageData.message_id) {
          const feedbackContainer = document.createElement('div');
          feedbackContainer.className = 'feedback-container';
          feedbackContainer.setAttribute('data-message-id', messageData.message_id);
          
          // Check if feedback already exists
          if (messageData.feedback) {
            
            // Show submitted feedback state
            const ratingIcon = messageData.feedback.rating === 'thumbs_up' ? 'thumb_up' : 'thumb_down';
            const ratingClass = messageData.feedback.rating === 'thumbs_up' ? 'thumbs-up' : 'thumbs-down';
            const ratingLabel = messageData.feedback.rating === 'thumbs_up' ? 'Helpful' : 'Not Helpful';
            
            feedbackContainer.innerHTML = `
              <div class="feedback-buttons feedback-submitted">
                <button class="feedback-btn ${ratingClass} selected" disabled>
                  <span class="material-icons">${ratingIcon}</span>
                  <span class="feedback-label">${ratingLabel}</span>
                </button>
                ${messageData.feedback.reason ? `<span class="feedback-reason-display">Reason: ${escapeHtml(messageData.feedback.reason)}</span>` : ''}
              </div>
            `;
          } else {
            // No feedback yet - show interactive buttons
            feedbackContainer.innerHTML = `
              <div class="feedback-buttons">
                <button class="feedback-btn thumbs-up" data-rating="thumbs_up" title="Helpful">
                  <span class="material-icons">thumb_up</span>
                  <span class="feedback-label">Helpful</span>
                </button>
                <button class="feedback-btn thumbs-down" data-rating="thumbs_down" title="Not Helpful">
                  <span class="material-icons">thumb_down</span>
                  <span class="feedback-label">Not Helpful</span>
                </button>
              </div>
              <div class="feedback-form" style="display: none;">
                <select class="feedback-reason" required>
                  <option value="">Select reason...</option>
                  <option value="accurate">Accurate</option>
                  <option value="helpful">Helpful</option>
                  <option value="complete">Complete</option>
                  <option value="incorrect">Incorrect</option>
                  <option value="irrelevant">Irrelevant</option>
                  <option value="too_short">Too Short</option>
                  <option value="too_long">Too Long</option>
                  <option value="incomplete">Incomplete</option>
                  <option value="unsafe">Unsafe</option>
                  <option value="other">Other</option>
                </select>
                <textarea class="feedback-comment" placeholder="Additional comments (optional)..." rows="2"></textarea>
                <div class="feedback-actions">
                  <button class="feedback-submit-btn">Submit Feedback</button>
                  <button class="feedback-cancel-btn">Cancel</button>
                </div>
              </div>
              <div class="feedback-success" style="display: none;">
                <span class="material-icons">check_circle</span>
                <span>Thank you for your feedback!</span>
              </div>
            `;
          }
          
          contentElement.appendChild(feedbackContainer);
        }
      }
    }

    messageElement.appendChild(contentElement);
    if (isError) {
      messageElement.classList.add("error");
    }
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function addLoadingIndicator() {
    if (loadingIndicatorElement) return;
    loadingIndicatorElement = document.createElement("div");
    loadingIndicatorElement.classList.add("message", "received");
    // Add a span for the timer
    loadingIndicatorElement.innerHTML = `
        <div class="message-content" style="display: flex; align-items: center; gap: 10px;">
            <div class="loader"></div>
            <span class="elapsed-time">Thinking... (0s)</span>
        </div>`;
    chatMessages.appendChild(loadingIndicatorElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Start the timer
    elapsedSeconds = 0;
    const timerElement = loadingIndicatorElement.querySelector(".elapsed-time");
    loadingTimerInterval = setInterval(() => {
      elapsedSeconds++;
      if (timerElement) {
        timerElement.textContent = `Thinking... (${elapsedSeconds}s)`;
      }
    }, 1000);
  }

  function removeLoadingIndicator() {
    // Stop the timer first
    if (loadingTimerInterval) {
      clearInterval(loadingTimerInterval);
      loadingTimerInterval = null;
    }
    elapsedSeconds = 0; // Reset counter

    // Then remove the element
    if (loadingIndicatorElement) {
      loadingIndicatorElement.remove();
      loadingIndicatorElement = null;
    }
  }


  function resetSendButton() {
    sendButton.disabled = false;
    sendButton.innerHTML = sendIcon;
  }

  // --- CHAT SESSION & HISTORY MANAGEMENT (API-driven) ---

  async function fetchSessions(userId) {
    if (!userId) return [];
    try {
      const response = await fetch(`/api/user/${userId}/sessions`);
      if (!response.ok)
        throw new Error(`Network response was not ok: ${response.statusText}`);
      const data = await response.json();
      return data.sessions || [];
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
      return []; // Return empty array on error
    }
  }

  async function fetchSessionHistory(sessionId) {
    if (!sessionId) return;
    chatMessages.innerHTML = ""; // Clear previous messages
    addLoadingIndicator();
    try {
      const response = await fetch(`/api/analytics/session/${sessionId}/messages?limit=100&offset=0`);
      if (!response.ok)
        throw new Error(`Network response was not ok: ${response.statusText}`);
      const data = await response.json();
      const parsedMessages = parseHistoryResponse(data);

      removeLoadingIndicator();
      
      // STEP 1: Render all messages immediately (without feedback)
      for (const msg of parsedMessages) {
        addMessageToUI(msg.sender, msg.data);
      }
      
      // STEP 2: Fetch feedback in parallel and hydrate the UI as it loads
      const assistantMessagesWithId = parsedMessages.filter(
        (msg) => msg.sender === 'assistant' && msg.data && msg.data.message_id
      );
      
      if (assistantMessagesWithId.length > 0) {
        // Fire all feedback requests in parallel (don't await)
        Promise.all(
          assistantMessagesWithId.map(async (msg) => {
            const messageId = msg.data.message_id;
            try {
              const feedbackResponse = await fetch(`/api/get_feedback/${messageId}`);
              if (feedbackResponse.ok) {
                const feedbackData = await feedbackResponse.json();
                if (feedbackData.success && feedbackData.feedback) {
                  // Hydrate the UI with feedback data
                  hydrateFeedbackUI(messageId, feedbackData.feedback);
                }
              }
            } catch (error) {
              console.error(`Failed to fetch feedback for message ${messageId}:`, error);
              // Continue without feedback for this message
            }
          })
        ).catch((error) => {
          console.error("Error loading feedback:", error);
        });
      }
    } catch (error) {
      removeLoadingIndicator();
      addMessageToUI(
        "assistant",
        `Failed to load chat history: ${error.message}`,
        true
      );
      console.error("Failed to fetch session history:", error);
    }
  }

  async function renderChatList() {
    const userId = userIdInput.value;
    const sessions = await fetchSessions(userId);
    const currentSessionId = sessionIdInput.value;

    chatList.innerHTML = ""; // Clear the list

    // Use the session list from the API, already sorted by `last_message_time`
    sessions.forEach((session) => {
      const listItem = document.createElement("div");
      listItem.classList.add("chat-list-item");
      if (session.session_id === currentSessionId) {
        listItem.classList.add("active");
      }
      listItem.dataset.sessionId = session.session_id;

      const p = document.createElement("p");
      // We don't have a title from the API, so we'll use the ID for now.
      // A more advanced implementation might fetch the first message.
      p.textContent = `Chat ${session.session_id}`;
      p.title = `Session ID: ${session.session_id}\nLast Active: ${new Date(
        session.last_message_time
      ).toLocaleString()}`;
      listItem.appendChild(p);

      chatList.appendChild(listItem);
    });
  }

  async function loadChat(sessionId) {
    sessionIdInput.value = sessionId;
    await fetchSessionHistory(sessionId);
    await renderChatList(); // Re-render to set the active class
    messageInput.focus();
  }

  function startNewChat() {
    ensureUserId();

    const newSessionId = generateUUID();
    sessionIdInput.value = newSessionId;
    chatMessages.innerHTML = ""; // Clear the chat window

    // De-activate all other list items
    document.querySelectorAll(".chat-list-item").forEach((item) => {
      item.classList.remove("active");
    });

    // Create and prepend a new list item showing the session ID
    const newListItem = document.createElement("div");
    newListItem.classList.add("chat-list-item", "active");
    newListItem.dataset.sessionId = newSessionId;

    const p = document.createElement("p");
    // UPDATE: Display the new session ID directly.
    p.textContent = `Chat ${newSessionId}`;
    p.title = `Session ID: ${newSessionId}`;
    newListItem.appendChild(p);

    // Add the new item to the top of the chat list
    chatList.prepend(newListItem);

    // Clear inputs and focus
    messageInput.value = "";
    currentImageFile = null;
    imageInput.value = "";
    imagePreviewContainer.innerHTML = "";
    imageInputLabel.classList.remove("active");
    messageInput.focus();
  }

  async function sendMessage() {
    const text = messageInput.value.trim();
    const imageFileToProcess = currentImageFile;
    const userId = userIdInput.value.trim();
    const deviceNumber = deviceNumberInput.value.trim();
    const sessionId = sessionIdInput.value;

    if (!text && !imageFileToProcess) return;

    // Add user message to UI immediately
    addMessageToUI("user", {
      text: text,
      imageName: imageFileToProcess ? imageFileToProcess.name : null,
    });

    // Clear inputs
    const messageToClear = messageInput.value; // Keep it for the payload
    messageInput.value = "";
    currentImageFile = null;
    imageInput.value = "";
    imagePreviewContainer.innerHTML = "";
    imageInputLabel.classList.remove("active");

    // Show loading state
    sendButton.disabled = true;
    sendButton.innerHTML = thinkingIcon;
    addLoadingIndicator();

    // Prepare and send API payload to the /api/chat endpoint
    const payload = {
      user_id: userId,
      session_id: sessionId,
      input: {},
      metadata: {
        platform: "demo_ui",
        device: {
          device_number: deviceNumber ? deviceNumber : "",
          connection_status: deviceConnectionToggle.checked ? "connected" : "disconnected"
        }
      },
    };
    if (text) {
      payload.input.text = text;
    }

    try {
      // Always keep multi-agent on to preserve API format
      const url = `/api/chat?multi=on`;

      if (imageFileToProcess) {
        const reader = new FileReader();
        reader.onload = async (e) => {
          payload.input.image = { url: e.target.result };
          const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
          if (!response.ok) throw new Error((await response.json()).detail || 'Server error');
          const data = await response.json();
          removeLoadingIndicator();
          addMessageToUI('assistant', data);
        };
        reader.onerror = () => { throw new Error('Error reading image file.'); };
        reader.readAsDataURL(imageFileToProcess);
      } else {
        const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        if (!response.ok) throw new Error((await response.json()).detail || 'Server error');
        const data = await response.json();
        removeLoadingIndicator();
        addMessageToUI('assistant', data);
      }
    } catch (error) {
      removeLoadingIndicator();
      addMessageToUI('assistant', `Error: ${error.message}`, true);
    } finally {
      resetSendButton();
      // Refresh the chat list to show this session as the most recent
      await renderChatList();
    }
  }

  // --- EVENT LISTENERS ---

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage();
  });
  messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  newChatButton.addEventListener("click", startNewChat);

  chatList.addEventListener("click", (e) => {
    const target = e.target.closest(".chat-list-item");
    if (target && target.dataset.sessionId) {
      loadChat(target.dataset.sessionId);
    }
  });

  userIdInput.addEventListener("change", async () => {
    // When user ID changes, fetch their sessions and load the latest one
    const sessions = await fetchSessions(userIdInput.value);
    if (sessions.length > 0) {
      loadChat(sessions[0].session_id); // API returns sorted by most recent
    } else {
      startNewChat(); // If user has no sessions, start a new one
    }
  });

  // Save device connection preference to localStorage
  deviceConnectionToggle.addEventListener('change', () => {
    localStorage.setItem('deviceConnectionEnabled', deviceConnectionToggle.checked);
  });

  // Other event listeners (image input, action cards) are unchanged
  imageInput.addEventListener("change", (event) => {
    currentImageFile = event.target.files[0];
    imagePreviewContainer.innerHTML = "";
    if (currentImageFile) {
      imageInputLabel.classList.add("active");
      const reader = new FileReader();
      reader.onload = (e) => {
        const imgWrapper = document.createElement("div");
        imgWrapper.className = "image-preview-wrapper";
        imgWrapper.innerHTML = `<img src="${e.target.result
          }" class="image-preview" title="${escapeHtml(
            currentImageFile.name
          )}"><button class="remove-image-btn">&times;</button>`;
        imagePreviewContainer.appendChild(imgWrapper);
        imgWrapper
          .querySelector(".remove-image-btn")
          .addEventListener("click", () => {
            currentImageFile = null;
            imageInput.value = "";
            imagePreviewContainer.innerHTML = "";
            imageInputLabel.classList.remove("active");
          });
      };
      reader.readAsDataURL(currentImageFile);
    } else {
      imageInputLabel.classList.remove("active");
    }
  });

  chatMessages.addEventListener("click", (e) => {
    const target = e.target.closest(".action-card");
    if (!target) return;

    const type = target.dataset.type;
    const actionId = target.dataset.actionId;

    // Intercept device-type action cards with the two allowed action_ids
    if (
      type === "device" &&
      (actionId === "redirect:setup_chatbot360" || actionId === "redirect:clean_device")
    ) {
      // Show "Redirecting..." message in the chat
      addMessageToUI("assistant", { response: "Redirecting..." });
      return; // Do NOT send to LLM
    }

    // Default: send as chat message
    messageInput.value = target.dataset.value;
    sendMessage();
  });

  async function fetchAndRenderHomeCards() {
    const container = document.getElementById("home-cards-container");

    if (!container) {
      console.error("home-cards-container not found in DOM");
      return;
    }

    container.innerHTML = "";

    try {
      const response = await fetch("/api/home-cards?status=online");

      if (!response.ok) {
        throw new Error("Failed to fetch home cards");
      }

      const onlineCards = await response.json();

      if (onlineCards.length === 0) {
        container.innerHTML =
          '<p class="no-home-cards">No home cards available.</p>';
        return;
      }

      onlineCards.forEach((card) => {
        const cardDiv = document.createElement("div");
        cardDiv.className = "home-card";
        cardDiv.innerHTML = `<h3>${card.title}</h3><p>${card.prompt}</p>`;
        cardDiv.addEventListener("click", () => {
          messageInput.value = card.prompt;
          sendMessage();
        });
        container.appendChild(cardDiv);
      });
    } catch (e) {
      console.error("Error loading home cards:", e);
      container.innerHTML =
        '<p class="error-message">Could not load home cards.</p>';
    }
  }

  async function initialize() {
    // Load saved device connection preference
    const savedDeviceConnection = localStorage.getItem('deviceConnectionEnabled');
    if (savedDeviceConnection !== null) {
      deviceConnectionToggle.checked = savedDeviceConnection === 'true';
    }

    await fetchAndRenderHomeCards();
    // First, check the URL for an 'action' command
    const urlParams = new URLSearchParams(window.location.search);
    const action = urlParams.get("action");

    if (action === "new") {
      // If the URL is ?action=new, start a new chat right away.
      startNewChat();

      // Clean the URL to prevent re-triggering on refresh.
      // This removes the "?action=new" part from the browser's address bar.
      window.history.replaceState({}, document.title, window.location.pathname);
      return; // Stop the function here.
    }

    // --- If no action is found, run the original default logic ---
    if (!userIdInput.value) {
      userIdInput.value = "gpol"; // Default user for demo
    }

    const sessions = await fetchSessions(userIdInput.value);
    if (sessions.length > 0) {
      // Load the most recent chat session
      await loadChat(sessions[0].session_id);
    } else {
      // Or start a new chat if the user has no history
      startNewChat();
    }
  }

 // --- FEEDBACK FUNCTIONALITY ---


  /**
   * Hydrates the feedback UI with existing feedback data
   * This is used when loading chat history to update the UI after messages are rendered
   */
  function hydrateFeedbackUI(messageId, feedbackData) {
    // Find the feedback container for this message
    const feedbackContainer = document.querySelector(
      `.feedback-container[data-message-id="${messageId}"]`
    );
    
    if (!feedbackContainer) {
      return; // Message not found in UI
    }
    
    // Update the feedback container with submitted state (matching original format)
    const ratingIcon = feedbackData.rating === 'thumbs_up' ? 'thumb_up' : 'thumb_down';
    const ratingClass = feedbackData.rating === 'thumbs_up' ? 'thumbs-up' : 'thumbs-down';
    const ratingLabel = feedbackData.rating === 'thumbs_up' ? 'Helpful' : 'Not Helpful';
    
    feedbackContainer.innerHTML = `
      <div class="feedback-buttons feedback-submitted">
        <button class="feedback-btn ${ratingClass} selected" disabled>
          <span class="material-icons">${ratingIcon}</span>
          <span class="feedback-label">${ratingLabel}</span>
        </button>
        ${feedbackData.reason ? `<span class="feedback-reason-display">Reason: ${escapeHtml(feedbackData.reason)}</span>` : ''}
      </div>
    `;
  }

  async function submitFeedback(messageId, rating, reason, comment) {
    const userId = userIdInput.value.trim();
    const sessionId = sessionIdInput.value.trim();

    if (!userId || !sessionId) {
      console.error('User ID or Session ID is missing');
      return { success: false, message: 'User ID or Session ID is missing' };
    }

    try {
      const response = await fetch('/api/post_feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messageId: messageId,
          sessionId: sessionId,
          userId: userId,
          rating: rating,
          reason: reason,
          comment: comment || '',
          timestamp: new Date().toISOString(),
          branch: 'mvp-1',
        }),
      });

      // Handle HTTP error responses (400, 404, 409, 500)
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        const errorMessage = errorData.detail || errorData.message || 'Failed to submit feedback';
        console.error(`Feedback submission failed (${response.status}):`, errorMessage);
        return { success: false, message: errorMessage };
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error submitting feedback:', error);
      return { success: false, message: 'Network error: Failed to submit feedback' };
    }
  }

  function handleFeedbackButtonClick(event) {
    const button = event.currentTarget;
    const feedbackContainer = button.closest('.feedback-container');
    const rating = button.getAttribute('data-rating');
    const feedbackForm = feedbackContainer.querySelector('.feedback-form');
    const feedbackButtons = feedbackContainer.querySelector('.feedback-buttons');

    // Mark button as selected
    feedbackButtons.querySelectorAll('.feedback-btn').forEach(btn => btn.classList.remove('selected'));
    button.classList.add('selected');

    // Show the feedback form
    feedbackForm.style.display = 'block';
    feedbackForm.setAttribute('data-selected-rating', rating);

    // Focus on reason dropdown
    feedbackForm.querySelector('.feedback-reason').focus();
  }

  async function handleFeedbackSubmit(event) {
    const submitButton = event.currentTarget;
    const feedbackContainer = submitButton.closest('.feedback-container');
    const feedbackForm = feedbackContainer.querySelector('.feedback-form');
    const messageId = feedbackContainer.getAttribute('data-message-id');
    const rating = feedbackForm.getAttribute('data-selected-rating');
    const reason = feedbackForm.querySelector('.feedback-reason').value;
    const comment = feedbackForm.querySelector('.feedback-comment').value;

    if (!reason) {
      alert('Please select a reason for your feedback');
      return;
    }

    // Disable submit button and show loading
    submitButton.disabled = true;
    submitButton.textContent = 'Submitting...';

    // Submit feedback
    const result = await submitFeedback(messageId, rating, reason, comment);

    if (result.success) {
      // Hide form and buttons, show success message
      feedbackContainer.querySelector('.feedback-buttons').style.display = 'none';
      feedbackForm.style.display = 'none';
      const successMessage = feedbackContainer.querySelector('.feedback-success');
      successMessage.style.display = 'flex';
    } else {
      // Show error
      alert(result.message || 'Failed to submit feedback');
      submitButton.disabled = false;
      submitButton.textContent = 'Submit Feedback';
    }
  }

  function handleFeedbackCancel(event) {
    const cancelButton = event.currentTarget;
    const feedbackContainer = cancelButton.closest('.feedback-container');
    const feedbackForm = feedbackContainer.querySelector('.feedback-form');
    const feedbackButtons = feedbackContainer.querySelector('.feedback-buttons');

    // Hide form and reset
    feedbackForm.style.display = 'none';
    feedbackForm.querySelector('.feedback-reason').value = '';
    feedbackForm.querySelector('.feedback-comment').value = '';
    feedbackButtons.querySelectorAll('.feedback-btn').forEach(btn => btn.classList.remove('selected'));
  }

  // Event delegation for feedback buttons (since they're dynamically added)
  chatMessages.addEventListener('click', function(event) {
    const target = event.target;
    
    // Check if clicked element or its parent is a feedback button
    const button = target.closest('.feedback-btn');
    if (button) {
      const feedbackContainer = button.closest('.feedback-container');
      const successMessage = feedbackContainer?.querySelector('.feedback-success');
      // Only handle if feedback hasn't been submitted yet
      if (successMessage && successMessage.style.display !== 'none') {
        return; // Already submitted
      }
      handleFeedbackButtonClick({ currentTarget: button });
      return;
    }
    
    // Check for submit button
    const submitBtn = target.closest('.feedback-submit-btn');
    if (submitBtn) {
      handleFeedbackSubmit({ currentTarget: submitBtn });
      return;
    }
    
    // Check for cancel button
    const cancelBtn = target.closest('.feedback-cancel-btn');
    if (cancelBtn) {
      handleFeedbackCancel({ currentTarget: cancelBtn });
      return;
    }
  });

  initialize();

  // Make function globally accessible for debugging
  window.fetchAndRenderHomeCards = fetchAndRenderHomeCards;

  // Function to open hardware context in new tab
  function openHardwareContext() {
    const deviceNumber = deviceNumberInput.value.trim();
    if (!deviceNumber) {
      alert('Please enter a device number first.');
      return;
    }

    const url = `/api/hardware/context/${encodeURIComponent(deviceNumber)}`;
    window.open(url, '_blank');
  }

  // Make function globally accessible
  window.openHardwareContext = openHardwareContext;
});