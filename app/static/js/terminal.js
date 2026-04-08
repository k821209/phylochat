/**
 * Web terminal using xterm.js + WebSocket PTY.
 * Runs Claude Code directly in the browser.
 */
const PhyloTerminal = (() => {
    let term = null;
    let ws = null;
    let fitAddon = null;

    function setStatus(state) {
        const el = document.getElementById('terminal-status');
        if (!el) return;
        el.className = 'terminal-status ' + state;
        el.title = state === 'connected' ? 'Connected' : 'Disconnected';
    }

    function init() {
        term = new Terminal({
            cursorBlink: true,
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace",
            theme: {
                background: '#0d1117',
                foreground: '#c9d1d9',
                cursor: '#4cc9f0',
                selectionBackground: '#264f78',
                black: '#0d1117',
                red: '#ff7b72',
                green: '#7ee787',
                yellow: '#d29922',
                blue: '#79c0ff',
                magenta: '#d2a8ff',
                cyan: '#a5d6ff',
                white: '#c9d1d9',
            },
            scrollback: 5000,
        });

        fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);

        const container = document.getElementById('terminal-container');
        term.open(container);
        fitAddon.fit();

        // Connect WebSocket
        connect();

        // Handle resize
        window.addEventListener('resize', () => {
            fitAddon.fit();
            sendResize();
        });

        // ResizeObserver for panel resize
        const observer = new ResizeObserver(() => {
            fitAddon.fit();
            sendResize();
        });
        observer.observe(container);

        term.onData(data => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(new TextEncoder().encode(data));
            }
        });
    }

    function connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${location.host}/ws/terminal`);
        ws.binaryType = 'arraybuffer';

        ws.onopen = () => {
            setStatus('connected');
            sendResize();
        };

        ws.onmessage = (event) => {
            const data = new Uint8Array(event.data);
            term.write(data);
        };

        ws.onclose = () => {
            setStatus('disconnected');
            term.write('\r\n\x1b[31m[Terminal disconnected. Refresh to reconnect.]\x1b[0m\r\n');
        };

        ws.onerror = () => {
            setStatus('disconnected');
        };
    }

    function sendResize() {
        if (ws && ws.readyState === WebSocket.OPEN && term) {
            ws.send(`RESIZE:${term.cols}:${term.rows}`);
        }
    }

    function sendCommand(cmd) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(new TextEncoder().encode(cmd + '\n'));
        }
    }

    return { init, sendCommand };
})();
