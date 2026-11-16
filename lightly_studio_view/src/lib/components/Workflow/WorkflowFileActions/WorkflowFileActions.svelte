<script lang="ts">
    import type { WorkflowFile } from '$lib/hooks';
    import { Button } from '$lib/components/ui/button';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { toast } from 'svelte-sonner';
    import { flagsText, SEND_BACK_NEEDS_FLAG } from '../workflowFileTexts';

    type WorkflowFileState = WorkflowFile['state'];

    interface Props {
        file: Pick<WorkflowFile, 'state' | 'your_role' | 'can_edit'>;
        /** Flags on the file nobody cleared yet. */
        openFlags: number;
        /** A move is waiting for the workflow service. */
        transitioning: boolean;
        /** Moves the file; resolves once the service confirmed it. */
        onTransition: (state: WorkflowFileState) => Promise<void>;
    }

    const { file, openFlags, transitioning, onTransition }: Props = $props();

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
        {#if file.state === 'rework' && openFlags > 0}
            <span class="text-sm text-muted-foreground">{flagsText(openFlags)} to address</span>
        {/if}
        <Button size="sm" disabled={transitioning} onclick={() => move('in_review')}
            >{transitioning ? 'Submitting…' : 'Submit for review'}</Button
        >
    </div>
{:else if canReview}
    <div class="flex items-center gap-3" data-testid="workflow-file-actions">
        {#if openFlags > 0}
            <span class="text-sm text-muted-foreground"
                >Accepting clears {flagsText(openFlags, 'open flag')}</span
            >
        {/if}
        {#if openFlags === 0}
            <Tooltip
                content={SEND_BACK_NEEDS_FLAG}
                position="bottom"
                triggerTabIndex={0}
                noTriggerRole
            >
                <Button
                    size="sm"
                    variant="outline"
                    class="disabled:opacity-45"
                    disabled
                    aria-describedby="workflow-send-back-reason">Send back to Rework (0)</Button
                >
            </Tooltip>
            <span id="workflow-send-back-reason" class="sr-only">{SEND_BACK_NEEDS_FLAG}</span>
        {:else}
            <Button
                size="sm"
                variant="outline"
                class="disabled:opacity-45"
                disabled={transitioning}
                onclick={() => move('rework')}
                >{pending('rework')
                    ? 'Sending back…'
                    : `Send back to Rework (${openFlags})`}</Button
            >
        {/if}
        <Button size="sm" disabled={transitioning} onclick={() => move('accepted')}
            >{pending('accepted') ? 'Accepting…' : 'Accept'}</Button
        >
    </div>
{/if}
