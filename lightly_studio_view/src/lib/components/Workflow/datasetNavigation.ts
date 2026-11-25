import type { SampleWorkflowView } from '$lib/api/lightly_studio_local';
import { WORKFLOW_BATCH_PARAM, WORKFLOW_PROJECT_PARAM } from '$lib/contexts/WorkflowFile.svelte';

/**
 * Shallow-routing state (`page.state.nav`) of a sample opened from the dataset grid.
 * Prev/next then follows the grid's filtered order, also in workflow mode. It is not a URL
 * param, so a hard reload or a batch link from the workspace steps in batch order.
 */
export const DATASET_NAV = 'dataset';

/** The `goto` options that open a sample from the dataset grid. */
export const datasetNavOptions = { state: { nav: DATASET_NAV } } as const;

/** The URL of a sample, with the batch params when the sample is in a batch. */
export function toWorkflowSampleURL(
    sampleURL: string,
    workflow: Pick<SampleWorkflowView, 'project_id' | 'batch_id'> | null | undefined
): string {
    if (!workflow) return sampleURL;
    const params = new URLSearchParams({
        [WORKFLOW_PROJECT_PARAM]: workflow.project_id,
        [WORKFLOW_BATCH_PARAM]: workflow.batch_id
    });
    return `${sampleURL}?${params}`;
}

/**
 * The URL of a neighbour in batch order: it keeps the current batch params, so the neighbour
 * opens in the same batch. The hash (e.g. the MCAP tick) belongs to the current sample and is
 * dropped.
 */
export function toBatchSampleURL(sampleURL: string, currentURL: URL): string {
    return `${sampleURL}${currentURL.search}`;
}

/**
 * Whether the sample page follows the batch instead of the dataset grid: prev/next steps
 * through the batch and the breadcrumb leads back to the batch.
 */
export function followsBatchOrder({
    workflowActive,
    state
}: {
    workflowActive: boolean;
    state: App.PageState;
}): boolean {
    return workflowActive && state.nav !== DATASET_NAV;
}
