// ===== Mermaid Init =====
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#6366f1',
    primaryTextColor: '#e2e4f0',
    primaryBorderColor: '#3a3f5c',
    lineColor: '#8b8fa8',
    secondaryColor: '#242736',
    tertiaryColor: '#1a1d27',
    background: '#1a1d27',
    mainBkg: '#242736',
    nodeBorder: '#3a3f5c',
    clusterBkg: '#1a1d27',
    titleColor: '#e2e4f0',
    edgeLabelBackground: '#242736',
    fontFamily: 'Inter, sans-serif',
  },
  flowchart: {
    htmlLabels: true,
    curve: 'basis',
  },
  securityLevel: 'loose',
});

function renderMermaid() {
  const elements = document.querySelectorAll('.mermaid:not([data-processed])');
  if (elements.length > 0) {
    mermaid.run({ nodes: elements }).catch(e => {
      console.warn('Mermaid render error:', e);
    });
  }
}

// Initial render
document.addEventListener('DOMContentLoaded', renderMermaid);

// Re-render after HTMX swaps
document.addEventListener('htmx:afterSwap', renderMermaid);
document.addEventListener('htmx:afterSettle', renderMermaid);

// ===== SSE Stream Handler =====
/**
 * Read an SSE stream response and append text chunks to a DOM element.
 * @param {Response} response - fetch Response with SSE stream
 * @param {HTMLElement} target - Element to append text to
 * @param {Function} onDone - Callback when stream finishes
 */
async function readSSEStream(response, target, onDone) {
  if (!response.ok) {
    const text = await response.text();
    target.textContent = `Error ${response.status}: ${text}`;
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            if (onDone) onDone();
            return;
          }
          // Unescape newlines
          const text = data.replace(/\\n/g, '\n');
          target.textContent += text;

          // Auto-scroll to bottom
          target.scrollTop = target.scrollHeight;
          const parent = target.closest('.chat-messages, .stream-box');
          if (parent) parent.scrollTop = parent.scrollHeight;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (onDone) onDone();
}

// ===== HTMX Configuration =====
document.addEventListener('htmx:configRequest', (e) => {
  // Add CSRF-like header for HTMX requests (not strictly needed but good practice)
  e.detail.headers['X-Requested-With'] = 'htmx';
});

// Re-render Mermaid after HTMX content loads
document.addEventListener('htmx:load', (e) => {
  const mermaidNodes = e.detail.elt.querySelectorAll('.mermaid:not([data-processed])');
  if (mermaidNodes.length > 0) {
    mermaid.run({ nodes: mermaidNodes }).catch(console.warn);
  }

  // Re-init Chart.js charts in loaded content
  if (typeof initKPICharts === 'function') {
    initKPICharts();
  }
});

// ===== Utility Functions =====

/**
 * Format a number with commas
 */
function formatNumber(n) {
  return new Intl.NumberFormat().format(n);
}

/**
 * Auto-resize textarea to content
 */
function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
}

// Apply auto-resize to all relevant textareas
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('textarea').forEach(ta => {
    ta.addEventListener('input', () => autoResize(ta));
  });
});

// ===== Tab switching (generic) =====
function switchTab(groupId, tabId, btn) {
  // Hide all panels for this group
  document.querySelectorAll(`[id^="tab-${groupId}-"]`).forEach(p => {
    p.classList.remove('active');
  });

  // Deactivate all buttons in this group's tab-buttons container
  const tabsContainer = document.getElementById(`tabs-${groupId}`);
  if (tabsContainer) {
    tabsContainer.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  }

  // Activate the selected panel and button
  const panel = document.getElementById(`tab-${groupId}-${tabId}`);
  if (panel) panel.classList.add('active');
  if (btn) btn.classList.add('active');
}

// ===== Copy to clipboard =====
function copyCode(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;

  const text = el.textContent || el.innerText;
  navigator.clipboard.writeText(text).then(() => {
    // Find and update the copy button
    const btn = event.target;
    const original = btn.textContent;
    btn.textContent = 'Copied!';
    btn.style.color = 'var(--success)';
    setTimeout(() => {
      btn.textContent = original;
      btn.style.color = '';
    }, 2000);
  }).catch(err => {
    console.warn('Copy failed:', err);
    // Fallback: select text
    const range = document.createRange();
    range.selectNode(el);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
  });
}

// ===== Mermaid custom styles for workflow flags =====
// Inject CSS classes for mermaid nodes after render
function injectMermaidStyles() {
  const style = document.createElement('style');
  style.textContent = `
    .mermaid .handoff rect, .mermaid .handoff polygon {
      fill: rgba(245,158,11,0.2) !important;
      stroke: #f59e0b !important;
    }
    .mermaid .redundant rect, .mermaid .redundant polygon {
      fill: rgba(239,68,68,0.2) !important;
      stroke: #ef4444 !important;
    }
    .mermaid .trigger rect, .mermaid .trigger polygon {
      fill: rgba(16,185,129,0.2) !important;
      stroke: #10b981 !important;
    }
  `;
  document.head.appendChild(style);
}

injectMermaidStyles();
