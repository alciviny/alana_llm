export interface IngestionJob {
    id: string;
    filename: string;
    status: string;
    total_batches: number;
    completed_batches: number;
}

export interface AgentEvent {
    type: string;
    data: {
        agent?: string; // NOVO: Quem está enviando o pensamento
        content?: string;
        name?: string;
        result?: string;
        command?: string;
        attempt?: number;
        total?: number;
        message?: string;
    };
}

export interface SearchResult {
    url: string;
    title: string;
    snippet: string;
}
