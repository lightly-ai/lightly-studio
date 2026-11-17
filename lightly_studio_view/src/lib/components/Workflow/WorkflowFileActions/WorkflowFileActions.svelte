<script lang="ts">
    import type { WorkflowFile } from '$lib/hooks';
    import { Button } from '$lib/components/ui/button';
    import { toast } from 'svelte-sonner';

    type WorkflowFileState = WorkflowFile['state'];

    interface Props {
        file: Pick<WorkflowFile, 'state' | 'your_role' | 'can_edit'>;
        /** A move is waiting for the workflow service. */
        transitioning: boolean;
        /** Moves the file; resolves once the service confirmed it. */
        onTransition: (state: WorkflowFileState) => Promise<void>;
    }

    const { file, transitioning, onTransition }: Props = $props();

    const canSubmit = $derived(
        file.your_role === 'labeler' &&
            file.can_edit &&
            (file.state === 'in_progress' || file.state === 'rework')
    );
    const canReview = $derived(
        file.your_role === 'reviewer' && file.can_edit && file.state === 'in_review'
    );

    let requested = $state<WorkflowFileState | null>(null);

    const move = async (state: WorkflowFileState) => {
        requested = state;
        try {
            await onTransition(state);
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Could not change the file state');
        } finally {
            requested = null;
        }
    };

    const pending = (state: WorkflowFileState) => transitioning && requested === state;
</script>

{#if canSubmit}
    <div class="flex items-center gap-3" data-testid="workflow-file-actions">
        <Button size="sm" disabled={transitioning} onclick={() => move('in_review')}
            >{transitioning ? 'Submitting…' : 'Submit for review'}</Button
        >
    </div>
{:else if canReview}
    <div class="flex items-center gap-3" data-testid="workflow-file-actions">
        <Button size="sm" variant="outline" disabled={transitioning} onclick={() => move('rework')}
            >{pending('rework') ? 'Sending back…' : 'Send back to Rework'}</Button
        >
        <Button size="sm" disabled={transitioning} onclick={() => move('accepted')}
            >{pending('accepted') ? 'Accepting…' : 'Accept'}</Button
        >
    </div>
{/if}
