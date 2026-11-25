import { goto } from '$app/navigation';
import { page } from '$app/state';
import { routeHelpers } from '$lib/routes';
import {
    datasetNavOptions,
    followsBatchOrder,
    toBatchSampleURL,
    toWorkflowSampleURL
} from '$lib/components/Workflow/datasetNavigation';
import { useAdjacentMcapSequences } from '$lib/hooks/useAdjacentMcapSequences/useAdjacentMcapSequences';
import type { createWorkflowFileContext } from '$lib/contexts/WorkflowFile.svelte';

interface Params {
    getSequenceId: () => string;
    getCollectionId: () => string;
    getCollectionType: () => string;
    workflow: Pick<ReturnType<typeof createWorkflowFileContext>, 'active' | 'file'>;
}

/** One neighbour: its place in the grid order and its place in the batch order. */
interface Neighbour {
    gridSequenceId: string | null | undefined;
    gridWorkflow: Parameters<typeof toWorkflowSampleURL>[1];
    batchSequenceId: string | null | undefined;
}

/**
 * The previous/next sequence handlers of the MCAP labeling page, or undefined at either end.
 *
 * Opened from the dataset grid, prev/next follows the grid, also in workflow mode: a neighbour
 * in a batch opens in workflow mode and keeps stepping in grid order. Opened from the batch
 * file list or a shared link, it steps through the batch and the neighbour opens in the same
 * batch. A neighbour opens on its first tick: the tick hash is not carried over.
 */
export const useSequenceNeighbours = ({
    getSequenceId,
    getCollectionId,
    getCollectionType,
    workflow
}: Params) => {
    const batchOrder = $derived(
        followsBatchOrder({ workflowActive: workflow.active, state: page.state })
    );
    // Neighbours in the sequences grid order of the SEQUENCE collection.
    const { query } = $derived(
        useAdjacentMcapSequences({ sampleId: getSequenceId(), collectionId: getCollectionId() })
    );
    const adjacent = $derived(query.data);

    const neighbourHandler = ({
        gridSequenceId,
        gridWorkflow,
        batchSequenceId
    }: Neighbour): (() => void) | undefined => {
        const sequenceId = batchOrder ? batchSequenceId : gridSequenceId;
        if (!sequenceId) return undefined;
        const sequenceURL = routeHelpers.toPointCloudLabeling({
            datasetId: page.params.dataset_id!,
            collectionType: getCollectionType(),
            collectionId: getCollectionId(),
            sequenceId
        });
        return batchOrder
            ? () => void goto(toBatchSampleURL(sequenceURL, page.url))
            : () => void goto(toWorkflowSampleURL(sequenceURL, gridWorkflow), datasetNavOptions);
    };

    return {
        /** True when the page follows the batch, false when it was opened from the grid. */
        get batchOrder() {
            return batchOrder;
        },
        get onPreviousSequence() {
            return neighbourHandler({
                gridSequenceId: adjacent?.previous_sample_id,
                gridWorkflow: adjacent?.previous_workflow,
                batchSequenceId: workflow.file?.previous_sample_id
            });
        },
        get onNextSequence() {
            return neighbourHandler({
                gridSequenceId: adjacent?.next_sample_id,
                gridWorkflow: adjacent?.next_workflow,
                batchSequenceId: workflow.file?.next_sample_id
            });
        }
    };
};
