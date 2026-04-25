document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const feedbackArea = document.getElementById('feedback-area');
    const progressBar = document.getElementById('progress-bar');
    const statusText = document.getElementById('status-text');
    const messageBox = document.getElementById('message-box');
    const messageText = document.getElementById('message-text');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    // Handle clicked files
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length === 0) return;
        
        // Take the first file
        const file = files[0];
        
        // Reset UI
        messageBox.classList.add('hidden');
        messageBox.className = 'message-box hidden';
        
        uploadFile(file);
    }

    function uploadFile(file) {
        // Show feedback area
        feedbackArea.classList.remove('hidden');
        progressBar.classList.add('loading');
        statusText.textContent = `Ingestão em curso: ${file.name}...`;
        dropZone.style.pointerEvents = 'none';
        dropZone.style.opacity = '0.5';

        const url = '/api/upload/';
        const formData = new FormData();
        formData.append('file', file);

        fetch(url, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            // Success
            showResult('success', data.message || 'Processado com sucesso!');
        })
        .catch(error => {
            // Error
            showResult('error', error.message || 'Ocorreu um erro na comunicação com a IA.');
        });
    }

    function showResult(type, text) {
        // Hide feedback
        feedbackArea.classList.add('hidden');
        progressBar.classList.remove('loading');
        dropZone.style.pointerEvents = 'auto';
        dropZone.style.opacity = '1';
        
        // Show message
        messageBox.classList.remove('hidden');
        messageBox.classList.add(type);
        messageText.textContent = text;
        
        // Reset file input
        fileInput.value = '';
    }

    // --- Tabs Logic ---
    window.switchTab = function switchTab(tab) {
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        
        document.getElementById(`${tab}-tab`).classList.add('active');
        document.querySelector(`button[onclick*="${tab}"]`).classList.add('active');

        if (tab === 'knowledge') {
            loadGraph();
        }
    };

    // --- Agent Logic ---
    const runMissionBtn = document.getElementById('run-mission-btn');
    const missionInput = document.getElementById('mission-input');
    const agentDisplay = document.getElementById('agent-display');
    const agentThought = document.getElementById('agent-thought');
    const agentCritique = document.getElementById('agent-critique');
    const agentTerminal = document.getElementById('agent-terminal');
    const approvalPanel = document.getElementById('approval-panel');
    const approveBtn = document.getElementById('approve-btn');
    const rejectBtn = document.getElementById('reject-btn');
    const approvalText = document.getElementById('approval-text');
    
    let agentSocket = null;

    runMissionBtn.addEventListener('click', () => {
        const mission = missionInput.value.trim();
        if (!mission) return alert('Por favor, descreva a missão para a Alana.');

        startAgentMission(mission);
    });

    // --- Approval Actions ---
    if (approveBtn) {
        approveBtn.addEventListener('click', () => {
            if (agentSocket && agentSocket.readyState === WebSocket.OPEN) {
                agentSocket.send(JSON.stringify({ action: 'approve' }));
                approvalPanel.classList.add('hidden');
                agentTerminal.textContent += `\n[SISTEMA]: Execução AUTORIZADA pelo operador.\n`;
            }
        });
    }

    if (rejectBtn) {
        rejectBtn.addEventListener('click', () => {
            if (agentSocket && agentSocket.readyState === WebSocket.OPEN) {
                agentSocket.send(JSON.stringify({ action: 'reject' }));
                approvalPanel.classList.add('hidden');
                agentTerminal.textContent += `\n[SISTEMA]: Execução ABORTADA pelo operador.\n`;
            }
        });
    }

    function startAgentMission(mission) {
        // UI Reset
        agentDisplay.classList.remove('hidden');
        agentThought.textContent = 'Executando análise de missão...';
        agentTerminal.textContent = '> Conectando ao sistema autônomo...\n';
        runMissionBtn.disabled = true;
        runMissionBtn.textContent = 'PROCESSANDO...';

        // Conexão WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/agent`;
        
        if (agentSocket) agentSocket.close();
        agentSocket = new WebSocket(wsUrl);

        agentSocket.onopen = () => {
            agentTerminal.textContent += '> Conexão estabelecida.\n> Enviando missão para a Engenheira...\n';
            agentSocket.send(JSON.stringify({ mission: mission }));
        };

        agentSocket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleAgentEvent(msg);
        };

        agentSocket.onerror = (error) => {
            agentTerminal.textContent += `\n[ERRO CRÍTICO]: Falha na conexão WebSocket.\n`;
            runMissionBtn.disabled = false;
            runMissionBtn.textContent = 'REEXECUTAR MISSÃO';
        };

        agentSocket.onclose = () => {
            agentTerminal.textContent += `\n> Fim da conexão com o sistema autônomo.\n`;
            runMissionBtn.disabled = false;
            runMissionBtn.textContent = 'NOVA MISSÃO';
        };
    }

    function handleAgentEvent(event) {
        const { type, data } = event;

        switch (type) {
            case 'thought':
                agentThought.textContent = data.content;
                // Efeito visual de brilho no pensamento
                agentThought.parentElement.style.boxShadow = '0 0 15px rgba(59, 130, 246, 0.3)';
                setTimeout(() => agentThought.parentElement.style.boxShadow = 'none', 500);
                break;

            case 'critique':
                if (agentCritique) {
                    agentCritique.textContent = data.content;
                    agentCritique.parentElement.style.boxShadow = '0 0 15px rgba(245, 158, 11, 0.3)';
                    setTimeout(() => agentCritique.parentElement.style.boxShadow = 'none', 500);
                }
                break;

            case 'tool_start':
                agentTerminal.textContent += `\n[AÇÃO]: Executando ferramenta '${data.name}'...\n`;
                if (data.args) {
                    agentTerminal.textContent += `[ARGS]: ${JSON.stringify(data.args, null, 2)}\n`;
                }
                break;

            case 'tool_result':
                agentTerminal.textContent += `\n[RESULTADO]:\n${data.result}\n`;
                break;

            case 'awaiting_approval':
                if (approvalPanel) {
                    approvalText.textContent = `A Alana solicita autorização para executar: ${data.command}`;
                    approvalPanel.classList.remove('hidden');
                    approvalPanel.scrollIntoView({ behavior: 'smooth' });
                }
                break;

            case 'mission_complete':
                agentTerminal.textContent += `\n[COMPLETO]: ${data.message}\n`;
                showResult('success', 'Missão finalizada com sucesso.');
                break;

            case 'mission_failed':
                agentTerminal.textContent += `\n[FALHA]: ${data.reason}\n`;
                showResult('error', 'Interrupção na missão.');
                break;

            case 'error':
                agentTerminal.textContent += `\n[SISTEMA]: ${data.message}\n`;
                break;
            
            case 'cycle_start':
                agentTerminal.textContent += `\n--- Ciclo ${data.attempt}/${data.total} ---\n`;
                break;
        }
        
        // Auto-scroll terminal
        agentTerminal.scrollTop = agentTerminal.scrollHeight;
    }

    // --- Log Console Logic ---
    const logText = document.getElementById('log-text');
    let isFetchingLogs = false;

    function fetchLogs() {
        if (isFetchingLogs) return;
        isFetchingLogs = true;

        fetch('/api/logs')
            .then(res => res.json())
            .then(data => {
                if (data.logs) {
                    const lines = data.logs.split('\n');
                    const formatted = lines.map(line => {
                        if (!line.trim()) return '';
                        let typeClass = 'log-info';
                        if (line.includes('ERROR') || line.includes('FALHA')) typeClass = 'log-error';
                        else if (line.includes('WARNING') || line.includes('AVISO')) typeClass = 'log-warn';
                        else if (line.includes('SUCCESS') || line.includes('SUCESSO')) typeClass = 'log-success';
                        
                        return `<div class="${typeClass}">${line}</div>`;
                    }).join('');
                    
                    logText.innerHTML = formatted;
                    logText.scrollTop = logText.scrollHeight;
                }
                isFetchingLogs = false;
            })
            .catch(err => {
                console.error("Erro na telemetria:", err);
                isFetchingLogs = false;
            });
    }

    // Knowledge Graph
    let network = null;

    async function loadGraph() {
        const container = document.getElementById('knowledge-graph');
        if (!container) return;

        try {
            const response = await fetch('/api/graph/data');
            const data = await response.json();

            const options = {
                nodes: {
                    shape: 'dot',
                    size: 20,
                    font: { size: 14, color: '#ffffff' },
                    borderWidth: 2,
                    shadow: true
                },
                edges: {
                    width: 2,
                    color: { inherit: 'from' },
                    smooth: { type: 'continuous' }
                },
                physics: {
                    stabilization: true,
                    barnesHut: {
                        gravitationalConstant: -2000,
                        springLength: 200
                    }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200
                }
            };

            if (network) {
                network.destroy();
            }

            network = new vis.Network(container, data, options);
            
            network.on("click", function (params) {
                if (params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    showToast(`Entidade: ${nodeId}`);
                }
            });

        } catch (error) {
            console.error("Erro ao carregar grafo:", error);
            showToast("Falha ao carregar mapa neural.");
        }
    }

    // Utility
    function showToast(text) {
        const box = document.getElementById('message-box');
        const txt = document.getElementById('message-text');
        txt.innerText = text;
        box.classList.remove('hidden');
        setTimeout(() => box.classList.add('hidden'), 3000);
    }

    // Init
    window.onload = () => {
        fetchLogs();
        setInterval(fetchLogs, 5000);
    };
});
