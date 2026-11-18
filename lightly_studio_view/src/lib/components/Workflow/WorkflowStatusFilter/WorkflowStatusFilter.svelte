<script lang="ts">
    import type { WorkflowStatus } from '$lib/api/lightly_studio_local';
    import { FilterList } from '$lib/components/FilterList';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { WORKFLOW_STATES } from '$lib/components/Workflow/workflowFileTexts';
    import { useWorkflowProject } from '$lib/hooks/useWorkflowProject/useWorkflowProject.svelte';
    import { useWorkflowStatusFilter } from '$lib/hooks/useWorkflowStatusFilter/useWorkflowStatusFilter';

    interface Props {
        collectionId: string;
    }

    const { collectionId }: Props = $props();

    const OPTIONS: { id: WorkflowStatus; label: string }[] = [
        { id: 'not_in_workflow', label: 'Not in workflow' },
        ...(['not_started', 'in_progress', 'in_review', 'rework', 'accepted'] as const).map(
            (state) => ({ id: state, label: WORKFLOW_STATES[state].label })
        )
    ];

    const project = useWorkflowProject(() => collectionId);
    const { selectedWorkflowStates, toggleWorkflowState, setWorkflowStates } = $derived(
        useWorkflowStatusFilter(collectionId)
    );

    const items = $derived(
        OPTIONS.map((option) => ({
            ...option,
            selected: $selectedWorkflowStates.includes(option.id)
        }))
    );
</script>

{#if project.projectId}
    <Segment title="Workflow status">
        <div class="mb-3 w-full space-y-2">
            <FilterList
                {items}
                onToggle={(id) => toggleWorkflowState(id as WorkflowStatus)}
                onSelectionChange={(ids) => setWorkflowStates(ids as WorkflowStatus[])}
                testId="workflow-status-filter"
                showSearch={false}
                paged={false}
            />
        </div>
    </Segment>
{/if}
