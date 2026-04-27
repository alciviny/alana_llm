import { IngestionJob, AgentEvent } from './types';

// --- Global Declarations for external libraries ---
declare const vis: any;

// --- DOM Elements ---
const getEl = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = getEl('drop-zone');
    const fileInput = getEl<HTMLInputElement>('file-input');
    const feedbackArea = getEl('feedback-area');
    const progressBar = getEl('progress-bar');
    const statusText = getEl('status-text');
    const messageBox = getEl('message-box');
    const messageText = getEl('message-text');
    const jobsList = getEl('jobs-list');

    // Agent Elements
    const runMissionBtn = getEl<HTMLButtonElement>('run-mission-btn');
    const missionInput = getEl<HTMLTextAreaElement>('mission-input');
    const agentDisplay = getEl('agent-display');
    const agentThought = getEl('agent-thought');
    const agentCritique = getEl('agent-critique');
    const agentTerminal = getEl('agent-terminal');
    const approvalPanel = getEl('approval-panel');
    const approveBtn = getEl('approve-btn');
    const rejectBtn = getEl('reject-btn');
    const approvalText = getEl('approval-text');
    const artifactGallery = getEl('artifact-gallery');

    const toolIndicators: Record<string, HTMLElement | null> = {
        'research': getEl('tool-research'),
        'python_runner': getEl('tool-simulation'),
        'validate_theory': getEl('tool-simulation'),
        'navigate_graph': getEl('tool-graph'),
        'autonomous_analyst': getEl('tool-graph')
    };

    const namespaceSelect = getEl<HTMLSelectElement>('namespace-select');
    let currentNamespace = namespaceSelect.value;

    let agentSocket: WebSocket | null = null;
    let isFetchingJobs = false;
    let isFetchingLogs = false;
    let network: any = null;

    // --- Namespace Management ---
    namespaceSelect.addEventListener('change', () => {
        currentNamespace = namespaceSelect.value;
        fetchIngestionJobs();
        if (getEl('knowledge-tab').classList.contains('active')) {
            loadGraph();
        }
    });

    // --- Tab Management ---
    const switchTab = (tabId: string) => {
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        
        const targetTab = getEl(`${tabId}-tab`);
        if (targetTab) targetTab.classList.add('active');
        
        const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
        if (btn) btn.classList.add('active');

        if (tabId === 'knowledge') {
            loadGraph();
        }
    };

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            if (tabId) switchTab(tabId);
        });
    });

    // --- Ingestion Logic ---
    const preventDefaults = (e: Event) => {
        e.preventDefault();
        e.stopPropagation();
    };

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    dropZone.addEventListener('dragenter', () => dropZone.classList.add('dragover'));
    dropZone.addEventListener('dragover', () => dropZone.classList.add('dragover'));
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e: DragEvent) => {
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer?.files;
        if (files) handleFiles(files);
    });

    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        if (fileInput.files) handleFiles(fileInput.files);
    });

    const handleFiles = (files: FileList) => {
        if (files.length === 0) return;
        const file = files[0];
        messageBox.classList.add('hidden');
        uploadFile(file);
    };

    const uploadFile = (file: File) => {
        feedbackArea.classList.remove('hidden');
        progressBar.classList.add('loading');
        statusText.textContent = `Ingestão em curso: ${file.name}...`;
        dropZone.style.pointerEvents = 'none';
        dropZone.style.opacity = '0.5';

        const formData = new FormData();
        formData.append('file', file);

        fetch(`/api/ingestion/upload?namespace=${currentNamespace}`, { method: 'POST', body: formData })
            .then(res => res.ok ? res.json() : res.json().then(e => { throw e; }))
            .then(data => showResult('success', data.message || 'Processado com sucesso!'))
            .catch(err => showResult('error', err.message || 'Erro na comunicação com a IA.'));
    };

    const showResult = (type: 'success' | 'error', text: string) => {
        feedbackArea.classList.add('hidden');
        progressBar.classList.remove('loading');
        dropZone.style.pointerEvents = 'auto';
        dropZone.style.opacity = '1';
        
        messageBox.className = `message-box ${type}`;
        messageText.textContent = text;
        fileInput.value = '';
        fetchIngestionJobs();
    };

    const fetchIngestionJobs = () => {
        if (isFetchingJobs) return;
        isFetchingJobs = true;
        fetch(`/api/ingestion/jobs?namespace=${currentNamespace}`)
            .then(res => res.json())
            .then(data => {
                renderJobs(data.jobs || []);
                isFetchingJobs = false;
            })
            .catch(() => isFetchingJobs = false);
    };

    const renderJobs = (jobs: IngestionJob[]) => {
        if (jobs.length === 0) {
            jobsList.innerHTML = '<div class="empty-jobs">Nenhum processo ativo no momento.</div>';
            return;
        }

        jobsList.innerHTML = jobs.map(job => {
            const progress = job.total_batches > 0 ? Math.round((job.completed_batches / job.total_batches) * 100) : 0;
            const statusClass = job.status.toLowerCase();
            return `
                <div class="job-item">
                    <div class="job-info">
                        <span class="job-filename">${job.filename}</span>
                        <span class="job-badge ${statusClass}">${job.status}</span>
                    </div>
                    <div class="job-progress-container">
                        <div class="job-progress-bar" style="width: ${progress}%"></div>
                    </div>
                    <div class="job-footer">
                        <span>${progress}% Concluído</span>
                        <span>${job.completed_batches}/${job.total_batches} Blocos</span>
                    </div>
                </div>`;
        }).join('');
    };

    // --- Agent Logic ---
    runMissionBtn.addEventListener('click', () => {
        const mission = missionInput.value.trim();
        if (!mission) return alert('Descreva a missão.');
        startAgentMission(mission);
    });

    const startAgentMission = (mission: string) => {
        agentDisplay.classList.remove('hidden');
        agentThought.textContent = 'Iniciando...';
        agentTerminal.innerHTML = '<div class="terminal-line system">> Conectando...</div>';
        runMissionBtn.disabled = true;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/agent?namespace=${currentNamespace}`;
        
        if (agentSocket) agentSocket.close();
        agentSocket = new WebSocket(wsUrl);

        agentSocket.onopen = () => agentSocket?.send(JSON.stringify({ mission, namespace: currentNamespace }));
        agentSocket.onmessage = (e) => handleAgentEvent(JSON.parse(e.data));
        agentSocket.onclose = () => {
            runMissionBtn.disabled = false;
            runMissionBtn.textContent = 'NOVA MISSÃO';
        };
    };

    const handleAgentEvent = (event: AgentEvent) => {
        const { type, data } = event;
        switch (type) {
            case 'thought':
                const agentPrefix = data.agent ? `[${data.agent}]: ` : '';
                agentThought.textContent = `${agentPrefix}${data.content}`;
                // Também adiciona ao terminal para histórico completo
                agentTerminal.innerHTML += `<div class="terminal-line thought"><strong>${agentPrefix}</strong>${data.content}</div>`;
                break;
            case 'tool_start':
                agentTerminal.innerHTML += `<div class="terminal-line tool-start">[AÇÃO]: ${data.name}...</div>`;
                if (data.name && toolIndicators[data.name]) {
                    toolIndicators[data.name]?.classList.add('active');
                }
                break;
            case 'tool_result':
                Object.values(toolIndicators).forEach(t => t?.classList.remove('active'));
                agentTerminal.innerHTML += `<div class="terminal-line result">${data.result}</div>`;
                break;
            case 'awaiting_approval':
                approvalText.textContent = `Autorizar: ${data.command}?`;
                approvalPanel.classList.remove('hidden');
                break;
            case 'mission_complete':
                showResult('success', 'Missão Completa');
                break;
        }
        agentTerminal.scrollTop = agentTerminal.scrollHeight;
    };

    approveBtn.addEventListener('click', () => {
        agentSocket?.send(JSON.stringify({ action: 'approve' }));
        approvalPanel.classList.add('hidden');
    });

    rejectBtn.addEventListener('click', () => {
        agentSocket?.send(JSON.stringify({ action: 'reject' }));
        approvalPanel.classList.add('hidden');
    });

    // --- Knowledge Graph ---
    // --- Knowledge Graph ---
    async function loadGraph() {
        const container = getEl('knowledge-graph');
        if (!container) return;
        try {
            const res = await fetch(`/api/graph/data?namespace=${currentNamespace}`);
            const data = await res.json();
            if (network) network.destroy();
            network = new vis.Network(container, data, {
                nodes: { shape: 'dot', size: 16, font: { color: '#fff' } },
                physics: { stabilization: true }
            });
        } catch (e) { console.error(e); }
    }
    
    getEl('refresh-graph-btn')?.addEventListener('click', loadGraph);

    // --- Logs ---
    const fetchLogs = () => {
        if (isFetchingLogs) return;
        isFetchingLogs = true;
        fetch('/api/logs')
            .then(res => res.json())
            .then(data => {
                if (data.logs) getEl('log-text').innerHTML = data.logs;
                isFetchingLogs = false;
            })
            .catch(() => isFetchingLogs = false);
    };

    // --- Init ---
    fetchLogs();
    fetchIngestionJobs();
    setInterval(fetchLogs, 5000);
    setInterval(fetchIngestionJobs, 3000);
});
