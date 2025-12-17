export type DatasetProgressState = 'pending' | 'indexing' | 'embedding' | 'ready' | 'error';

export interface DatasetProgress {
    dataset_id: string;
    state: DatasetProgressState;
    current: number;
    total: number;
    message: string;
    error: string | null;
    updated_at: string;
}

export interface ProgressUpdate {
    dataset_id: string;
    state: DatasetProgressState;
    current: number;
    total: number;
    message?: string;
}
