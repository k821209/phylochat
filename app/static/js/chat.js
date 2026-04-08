/**
 * Chat interface for PhyloChat.
 * Sends natural language requests, receives ggtree code + renders.
 */
const Chat = (() => {
    let sessionId = null;

    function setSessionId(id) { sessionId = id; }
    function getSessionId() { return sessionId; }

    async function send(message) {
        const treeId = TreeViewer.getTreeId();
        if (!treeId || !sessionId) return;

        // Add user message to UI
        _appendMessage('user', message);

        // Disable input
        const input = document.getElementById('chat-input');
        const btn = document.getElementById('btn-send');
        input.disabled = true;
        btn.disabled = true;

        // Show typing indicator
        const typing = _appendMessage('assistant', '⏳ Thinking...');

        try {
            const resp = await fetch('/chat/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    tree_id: treeId,
                    message: message,
                }),
            });

            const data = await resp.json();

            // Replace typing indicator
            typing.querySelector('p').textContent = data.content;

            // Update R code display
            if (data.r_code) {
                document.getElementById('r-code-display').querySelector('code').textContent = data.r_code;
            }

            // Update ggtree render
            if (data.render_url) {
                const img = document.getElementById('ggtree-image');
                img.src = data.render_url + '?t=' + Date.now();
                document.getElementById('ggtree-render').style.display = 'flex';
                document.getElementById('tree-viewer').style.display = 'none';
            }
        } catch (err) {
            typing.querySelector('p').textContent = '❌ Error: ' + err.message;
        } finally {
            input.disabled = false;
            btn.disabled = false;
            input.focus();
        }
    }

    function _appendMessage(role, text) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerHTML = `<p>${_escapeHtml(text)}</p>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div;
    }

    function _escapeHtml(text) {
        const el = document.createElement('span');
        el.textContent = text;
        return el.innerHTML;
    }

    return { send, setSessionId, getSessionId };
})();
