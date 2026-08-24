import type { RefineMode } from '$lib/services/types';
import { derived, writable, type Readable } from 'svelte/store';

interface ClassifierWorkflowState {
    phase: 'closed' | 'create' | 'refine';
    mode: RefineMode | null;
    classifierId: string | null;
    classifierName: string | null;
    classifierClasses: string[];
    confirmedPredictions: number;
    reviewedSamples: number;
    latestConfirmedPredictions: number | null;
    latestReviewedSamples: number | null;
    isPending: boolean;
}

const initialState: ClassifierWorkflowState = {
    phase: 'closed',
    mode: null,
    classifierId: null,
    classifierName: null,
    classifierClasses: [],
    confirmedPredictions: 0,
    reviewedSamples: 0,
    latestConfirmedPredictions: null,
    latestReviewedSamples: null,
    isPending: false
};

const workflow = writable<ClassifierWorkflowState>(initialState);
const isOpen = derived(workflow, ($workflow) => $workflow.phase !== 'closed');

export function useClassifierWorkflow(): {
    workflow: Readable<ClassifierWorkflowState>;
    isOpen: Readable<boolean>;
    openCreate: () => void;
    setTemporaryClassifier: (
        classifierId: string,
        classifierName: string,
        classifierClasses: string[]
    ) => void;
    openRefine: (
        mode: RefineMode,
        classifierId: string,
        classifierName: string,
        classifierClasses: string[]
    ) => void;
    recordReview: (confirmedPredictions: number, reviewedSamples: number) => void;
    setPending: (isPending: boolean) => void;
    close: () => void;
} {
    function openCreate() {
        workflow.set({ ...initialState, phase: 'create' });
    }

    function openRefine(
        mode: RefineMode,
        classifierId: string,
        classifierName: string,
        classifierClasses: string[]
    ) {
        workflow.update((state) => ({
            ...(state.phase === 'create' ? state : initialState),
            phase: 'refine',
            mode,
            classifierId,
            classifierName,
            classifierClasses
        }));
    }

    function setTemporaryClassifier(
        classifierId: string,
        classifierName: string,
        classifierClasses: string[]
    ) {
        workflow.update((state) => ({
            ...state,
            mode: 'temp',
            classifierId,
            classifierName,
            classifierClasses
        }));
    }

    function recordReview(confirmedPredictions: number, reviewedSamples: number) {
        workflow.update((state) => ({
            ...state,
            confirmedPredictions: state.confirmedPredictions + confirmedPredictions,
            reviewedSamples: state.reviewedSamples + reviewedSamples,
            latestConfirmedPredictions: confirmedPredictions,
            latestReviewedSamples: reviewedSamples
        }));
    }

    return {
        workflow,
        isOpen,
        openCreate,
        setTemporaryClassifier,
        openRefine,
        recordReview,
        setPending: (isPending) => workflow.update((state) => ({ ...state, isPending })),
        close: () => workflow.set(initialState)
    };
}
