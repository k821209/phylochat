/**
 * PhyloChat main app initialization.
 */
let lastRenderMtime = 0;
let lastRenderCount = 0;
let renderPollInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    TreeViewer.init();
    PhyloTerminal.init();
    initPanelDivider();
    initKeyboardShortcuts();

    // File upload handler
    document.getElementById('file-upload').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);
        await uploadTree(formData);
    });

    // Close modal on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hidePasteModal();
            toggleExplorer(false);
        }
    });

    // Close modal on backdrop click
    const pasteModal = document.getElementById('paste-modal');
    pasteModal.addEventListener('click', (e) => {
        if (e.target === pasteModal) hidePasteModal();
    });

    // Load file lists and start polling
    refreshExplorer();
    startRenderPolling();
});

/* ==========================================================
   FILE UPLOAD
   ========================================================== */

async function uploadTree(formData) {
    const uploadBtn = document.querySelector('[for="file-upload"]');
    uploadBtn.classList.add('loading');
    try {
        const resp = await fetch('/tree/upload', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();

        // Store IDs
        TreeViewer.setTreeId(data.tree_id);

        // Fetch and render tree
        const treeResp = await fetch(`/tree/${data.tree_id}/data`);
        const treeData = await treeResp.json();
        TreeViewer.render(treeData.tree_json);

        // Show export buttons
        showExportButtons(true);

        // Refresh tree list
        refreshExplorer();

        showToast('Tree loaded successfully', 'success');
    } catch (err) {
        showToast('Error uploading tree: ' + err.message, 'error');
    } finally {
        uploadBtn.classList.remove('loading');
    }
}

/* ==========================================================
   RENDER POLLING
   ========================================================== */

function startRenderPolling() {
    // Sync initial state without showing anything
    fetch('/render/latest').then(r => r.json()).then(data => {
        lastRenderMtime = data.mtime || 0;
    });
    refreshExplorer();

    // Lightweight poll: only check /render/latest (single small response)
    renderPollInterval = setInterval(async () => {
        try {
            const resp = await fetch('/render/latest');
            const data = await resp.json();

            if (data.file && data.mtime > lastRenderMtime) {
                const prevMtime = lastRenderMtime;
                lastRenderMtime = data.mtime;

                // Associate with active tree
                const activeTreeId = TreeViewer.getTreeId();
                if (activeTreeId) {
                    fetch(`/render/associate?filename=${encodeURIComponent(data.file)}&tree_id=${activeTreeId}`, { method: 'POST' });
                }

                // Auto-show only if a tree is active
                if (activeTreeId) {
                    showGgtreeRender(data.url);
                }

                updateRenderCount(null);
                refreshExplorer();
            }
        } catch (e) {
            // ignore
        }
    }, 3000);
}

function showGgtreeRender(url) {
    const img = document.getElementById('ggtree-image');
    const placeholder = document.getElementById('render-placeholder');
    img.src = url + '?t=' + Date.now();
    img.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';
    toggleView('render');
}

function updateRenderCount(count) {
    const badge = document.getElementById('render-count');
    if (!badge) return;
    if (count !== null) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-flex' : 'none';
    }
}

/* ==========================================================
   UNIFIED FILE EXPLORER (Tree → Renders hierarchy)
   ========================================================== */

async function refreshExplorer() {
    try {
        const [treesResp, rendersResp] = await Promise.all([
            fetch('/tree/list/all'),
            fetch('/render/by-tree'),
        ]);
        const trees = await treesResp.json();
        const renderData = await rendersResp.json();

        const container = document.getElementById('explorer-content');
        const activeId = TreeViewer.getTreeId();

        // Update badge
        const btn = document.getElementById('btn-explorer');
        let badge = btn?.querySelector('.explorer-badge');
        const totalCount = trees.length + lastRenderCount;
        if (totalCount > 0) {
            if (!badge && btn) {
                badge = document.createElement('span');
                badge.className = 'explorer-badge';
                btn.appendChild(badge);
            }
            if (badge) badge.textContent = totalCount;
        } else if (badge) {
            badge.remove();
        }

        if (trees.length === 0 && renderData.unassociated.length === 0) {
            container.innerHTML = '<div class="render-empty">No files yet.<br>Upload a tree to get started.</div>';
            return;
        }

        // Build grouped render lookup
        const rendersByTree = {};
        for (const group of renderData.grouped) {
            rendersByTree[group.tree_id] = group.renders;
        }

        let html = '';

        // Trees with their renders
        for (const t of trees) {
            const isActive = t.tree_id === activeId ? ' active' : '';
            const renders = rendersByTree[t.tree_id] || [];
            const renderCount = renders.length;

            html += `
                <div class="tree-group">
                    <div class="tree-group-header${isActive}" onclick="loadTree(${t.tree_id})" title="${t.filename}">
                        <span class="tree-group-icon">&#x1F333;</span>
                        <span class="tree-group-name">${t.filename}</span>
                        ${renderCount > 0 ? `<span class="tree-group-badge">${renderCount}</span>` : ''}
                        <button class="delete-btn" onclick="event.stopPropagation(); deleteTree(${t.tree_id})" title="Delete">&times;</button>
                    </div>
                    ${renderCount > 0 ? `
                        <div class="tree-group-renders">
                            ${renders.map(r => {
                                const time = new Date(r.mtime * 1000).toLocaleTimeString();
                                return `
                                    <div class="render-row" onclick="showGgtreeRender('${r.url}')" title="${r.file}">
                                        <span class="render-row-name">${r.file}</span>
                                        <span class="render-row-time">${time}</span>
                                        <button class="delete-btn" onclick="event.stopPropagation(); deleteRender('${r.file}')" title="Delete">&times;</button>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // Unassociated renders
        if (renderData.unassociated.length > 0) {
            html += '<div class="unassociated-header">Unlinked Renders</div>';
            html += '<div class="tree-group-renders">';
            for (const r of renderData.unassociated) {
                const time = new Date(r.mtime * 1000).toLocaleTimeString();
                html += `
                    <div class="render-row" onclick="showGgtreeRender('${r.url}')" title="${r.file}">
                        <span class="render-row-name">${r.file}</span>
                        <span class="render-row-time">${time}</span>
                        <button class="delete-btn" onclick="event.stopPropagation(); deleteRender('${r.file}')" title="Delete">&times;</button>
                    </div>
                `;
            }
            html += '</div>';
        }

        container.innerHTML = html;
    } catch (e) {
        // ignore
    }
}

async function loadTree(treeId) {
    try {
        const resp = await fetch(`/tree/${treeId}/data`);
        const data = await resp.json();
        TreeViewer.setTreeId(treeId);
        TreeViewer.render(data.tree_json);
        toggleView('d3');

        showExportButtons(true);
        refreshExplorer();

        // Load latest render for this tree if available
        const renderResp = await fetch('/render/by-tree');
        const renderData = await renderResp.json();
        for (const group of renderData.grouped) {
            if (group.tree_id === treeId && group.renders.length > 0) {
                const latest = group.renders[0];
                const img = document.getElementById('ggtree-image');
                const placeholder = document.getElementById('render-placeholder');
                img.src = latest.url + '?t=' + Date.now();
                img.style.display = 'block';
                if (placeholder) placeholder.style.display = 'none';
                break;
            }
        }
    } catch (e) {
        showToast('Error loading tree: ' + e.message, 'error');
    }
}

async function deleteTree(treeId) {
    try {
        await fetch(`/tree/${treeId}`, { method: 'DELETE' });
        if (TreeViewer.getTreeId() === treeId) {
            TreeViewer.setTreeId(null);
            showExportButtons(false);
        }
        refreshExplorer();
        showToast('Tree deleted', 'info');
    } catch (e) {
        // ignore
    }
}

async function deleteRender(filename) {
    try {
        await fetch(`/render/renders/${filename}`, { method: 'DELETE' });
        refreshRenderList();
        showToast('Render deleted', 'info');
    } catch (e) {
        // ignore
    }
}

/* ==========================================================
   PASTE MODAL
   ========================================================== */

function showPasteModal() {
    document.getElementById('paste-modal').style.display = 'flex';
    const input = document.getElementById('newick-input');
    input.value = '';
    input.focus();
}

function hidePasteModal() {
    document.getElementById('paste-modal').style.display = 'none';
}

async function submitPastedNewick() {
    const text = document.getElementById('newick-input').value.trim();
    if (!text) return;
    hidePasteModal();

    const formData = new FormData();
    formData.append('newick_text', text);
    await uploadTree(formData);
}

/* ==========================================================
   VIEW TOGGLE (Preview / Render)
   ========================================================== */

function toggleView(view) {
    const tabPreview = document.getElementById('tab-preview');
    const tabRender = document.getElementById('tab-render');

    const treeViewer = document.getElementById('tree-viewer');
    const ggtreeRender = document.getElementById('ggtree-render');

    if (view === 'd3') {
        treeViewer.style.display = '';
        ggtreeRender.style.display = 'none';
        tabPreview.classList.add('active');
        tabRender.classList.remove('active');
    } else {
        treeViewer.style.display = 'none';
        ggtreeRender.style.display = 'flex';
        tabPreview.classList.remove('active');
        tabRender.classList.add('active');
    }
}

/* ==========================================================
   EXPORT
   ========================================================== */

function showExportButtons(show) {
    const exportGroup = document.getElementById('toolbar-export');
    if (exportGroup) {
        exportGroup.style.display = show ? 'flex' : 'none';
    }
}

async function exportFigure(format) {
    const treeId = TreeViewer.getTreeId();
    if (!treeId) {
        showToast('No tree loaded', 'error');
        return;
    }

    // If requesting PNG and current render is PNG, download directly
    const img = document.getElementById('ggtree-image');
    if (img && img.src && !img.src.endsWith('/')) {
        const currentExt = img.src.split('.').pop().split('?')[0].toLowerCase();
        if (currentExt === format) {
            const link = document.createElement('a');
            link.href = img.src;
            link.download = `phylochat_tree.${format}`;
            link.click();
            showToast(`Downloading ${format.toUpperCase()}...`, 'info');
            return;
        }
    }

    // Generate via R for the requested format
    showToast(`Generating ${format.toUpperCase()}...`, 'info');
    window.open(`/export/figure?tree_id=${treeId}&format=${format}`, '_blank');
}

/* ==========================================================
   FILE EXPLORER (collapsible drawer)
   ========================================================== */

function toggleExplorer(forceState) {
    const explorer = document.getElementById('panel-explorer');
    const backdrop = document.getElementById('explorer-backdrop');
    const isOpen = explorer.classList.contains('open');
    const shouldOpen = forceState !== undefined ? forceState : !isOpen;

    if (shouldOpen) {
        explorer.classList.add('open');
        backdrop.classList.add('visible');
    } else {
        explorer.classList.remove('open');
        backdrop.classList.remove('visible');
    }
}

/* ==========================================================
   EXAMPLE CHIPS (send to terminal)
   ========================================================== */

function sendExamplePrompt(chipEl) {
    const text = chipEl.textContent.trim();
    PhyloTerminal.sendCommand(text);
    showToast('Sent to terminal: "' + text + '"', 'info');
}

/* ==========================================================
   CLAUDE SESSION MANAGEMENT
   ========================================================== */

let claudeRunning = false;

function launchClaude(mode) {
    if (claudeRunning) {
        showToast('Claude is already running', 'info');
        return;
    }

    const skipPerms = document.getElementById('toggle-skip-permissions').checked;

    let cmd = 'claude';
    if (mode === 'continue') cmd += ' --continue';
    cmd += ' --system-prompt "$(cat data/system_prompt.txt)"';
    if (skipPerms) cmd += ' --dangerously-skip-permissions';

    PhyloTerminal.sendCommand(cmd);
    claudeRunning = true;

    // Update button states
    document.getElementById('btn-new-claude').disabled = true;
    document.getElementById('btn-continue-claude').disabled = true;

    const modeLabel = mode === 'continue' ? 'Resuming' : 'Starting new';
    const permLabel = skipPerms ? ' (auto-accept)' : '';
    showToast(`${modeLabel} Claude session${permLabel}...`, 'info');
}

/* ==========================================================
   RESIZABLE PANEL DIVIDER
   ========================================================== */

function initPanelDivider() {
    const divider = document.getElementById('panel-divider');
    const panelTree = document.getElementById('panel-tree');
    const panelRight = document.getElementById('panel-right');
    const dashboard = document.querySelector('.dashboard');

    if (!divider || !panelTree || !panelRight) return;

    let isDragging = false;
    let startX = 0;
    let startTreeWidth = 0;

    divider.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        startTreeWidth = panelTree.getBoundingClientRect().width;
        divider.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        const dashboardWidth = dashboard.getBoundingClientRect().width;
        const dividerWidth = 5;
        const newTreeWidth = Math.max(320, Math.min(dashboardWidth - 320 - dividerWidth, startTreeWidth + dx));
        const newRightWidth = dashboardWidth - newTreeWidth - dividerWidth;

        panelTree.style.flex = 'none';
        panelTree.style.width = newTreeWidth + 'px';
        panelRight.style.flex = 'none';
        panelRight.style.width = newRightWidth + 'px';
    });

    document.addEventListener('mouseup', () => {
        if (!isDragging) return;
        isDragging = false;
        divider.classList.remove('dragging');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        // Trigger terminal resize
        window.dispatchEvent(new Event('resize'));
    });
}

/* ==========================================================
   KEYBOARD SHORTCUTS
   ========================================================== */

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Cmd/Ctrl+B: Toggle explorer
        if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
            e.preventDefault();
            toggleExplorer();
        }
        // Cmd/Ctrl+Shift+E: Export SVG
        if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'E') {
            e.preventDefault();
            exportFigure('svg');
        }
    });
}

/* ==========================================================
   TOAST NOTIFICATIONS
   ========================================================== */

function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(8px)';
        toast.style.transition = 'opacity 0.2s, transform 0.2s';
        setTimeout(() => toast.remove(), 200);
    }, duration);
}
