/**
 * ResearchOps Frontend Application
 * Team: Spideyx | GATEWAYS 2026
 *
 * Handles API health polling, metrics display, latency calculation, and error diagnostics.
 */

(function () {
    'use strict';

    // DOM Elements
    const elements = {
        endpointInput: document.getElementById('api-endpoint'),
        btnCheckHealth: document.getElementById('btn-check-health'),
        autoRefreshToggle: document.getElementById('auto-refresh'),
        healthPulse: document.getElementById('health-pulse'),
        metricStatus: document.getElementById('metric-status'),
        metricService: document.getElementById('metric-service'),
        metricLatency: document.getElementById('metric-latency'),
        metricLastChecked: document.getElementById('metric-last-checked'),
        responseStatusBadge: document.getElementById('response-status-badge'),
        jsonViewer: document.getElementById('json-viewer'),
    };

    let pollInterval = null;
    const POLL_INTERVAL_MS = 5000;

    /**
     * Resolve default health endpoint based on current page location.
     */
    function initializeEndpoint() {
        if (window.location.protocol.startsWith('http')) {
            // When served via FastAPI or a web server on localhost
            elements.endpointInput.value = `${window.location.origin}/api/health`;
        } else {
            // When opened as a local file (file://)
            elements.endpointInput.value = 'http://127.0.0.1:8000/api/health';
        }
    }

    /**
     * Fetch health status from backend API and update UI.
     */
    async function checkHealth() {
        const endpoint = elements.endpointInput.value.trim();
        if (!endpoint) return;

        // Visual loading state
        elements.metricStatus.textContent = 'Probing...';
        elements.metricStatus.className = 'metric-value';
        elements.healthPulse.className = 'pulse-indicator';

        const startTime = performance.now();
        const requestTime = new Date().toLocaleTimeString();

        try {
            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
                cache: 'no-cache',
            });

            const latencyMs = Math.round(performance.now() - startTime);
            const data = await response.json();

            // Update UI on successful response
            elements.metricLatency.textContent = `${latencyMs} ms`;
            elements.metricLastChecked.textContent = requestTime;
            elements.responseStatusBadge.textContent = `HTTP ${response.status}`;

            if (response.ok && data.status === 'ok') {
                elements.metricStatus.textContent = 'Healthy';
                elements.metricStatus.className = 'metric-value status-online';
                elements.metricService.textContent = data.service || 'unknown';
                elements.healthPulse.className = 'pulse-indicator pulse-online';
                elements.responseStatusBadge.className = 'pill-badge pill-success';
            } else {
                elements.metricStatus.textContent = 'Degraded';
                elements.metricStatus.className = 'metric-value status-error';
                elements.metricService.textContent = data.service || 'unknown';
                elements.healthPulse.className = 'pulse-indicator pulse-offline';
                elements.responseStatusBadge.className = 'pill-badge pill-error';
            }

            elements.jsonViewer.textContent = JSON.stringify(data, null, 2);
        } catch (error) {
            const latencyMs = Math.round(performance.now() - startTime);
            elements.metricLatency.textContent = `${latencyMs} ms`;
            elements.metricLastChecked.textContent = requestTime;
            elements.metricStatus.textContent = 'Offline';
            elements.metricStatus.className = 'metric-value status-error';
            elements.metricService.textContent = 'N/A';
            elements.healthPulse.className = 'pulse-indicator pulse-offline';
            elements.responseStatusBadge.textContent = 'ERR_CONN';
            elements.responseStatusBadge.className = 'pill-badge pill-error';

            elements.jsonViewer.textContent = JSON.stringify(
                {
                    error: 'Failed to connect to backend API',
                    message: error.message,
                    target_url: endpoint,
                    hint: 'Ensure the FastAPI backend is running via `python scripts/run_dev.py` or `uvicorn backend.app.main:app --port 8000`.',
                },
                null,
                2
            );
        }
    }

    /**
     * Start automatic periodic polling.
     */
    function startAutoPoll() {
        stopAutoPoll();
        pollInterval = setInterval(checkHealth, POLL_INTERVAL_MS);
    }

    /**
     * Stop automatic periodic polling.
     */
    function stopAutoPoll() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    // Event Listeners
    elements.btnCheckHealth.addEventListener('click', () => {
        checkHealth();
    });

    elements.autoRefreshToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            checkHealth();
            startAutoPoll();
        } else {
            stopAutoPoll();
        }
    });

    elements.endpointInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            checkHealth();
        }
    });

    // Initialize on DOM ready
    initializeEndpoint();
    checkHealth();
    if (elements.autoRefreshToggle.checked) {
        startAutoPoll();
    }
})();
