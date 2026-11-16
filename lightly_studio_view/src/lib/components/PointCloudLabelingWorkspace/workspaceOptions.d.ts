import type { WorkspaceCrumb } from './types';

/** Route inputs and host callbacks used to initialize a labeling workspace. */
export interface WorkspaceOptions {
    /** Dataset the labeled point-cloud sequence belongs to. */
    datasetId: string;
    /** GROUP collection containing the point cloud annotation sources. */
    annotationSourceCollectionId?: string;
    /** MCAP sequence being labeled, used to resolve per-tick camera frames. */
    sequenceId: string;
    /** 1-based tick to open on (from the route hash); defaults to the first frame. */
    tickNumber?: number;
    /** Reports the active tick as a 1-based number for route synchronization. */
    onTickChange?: (tickNumber: number) => void;
    /** Opens the previous sequence; the timeline control is disabled when absent. */
    onPreviousSequence?: () => void;
    /** Opens the next sequence; the timeline control is disabled when absent. */
    onNextSequence?: () => void;
    /** Dataset -> collection -> sample path of the point cloud being labeled. */
    sourcePath?: readonly WorkspaceCrumb[];
    /** Optional status override for tests and stories. */
    status?: 'unsupported' | 'empty' | 'error';
    /** Number of ticks to prefetch from the active tick forward. */
    prefetchTickCount?: number;
    /** Retries loading after a recoverable workspace error. */
    onRetry?: () => void;
}
