<script lang="ts">
    import CircleAlert from '@lucide/svelte/icons/circle-alert';
    import CircleStop from '@lucide/svelte/icons/circle-stop';
    import { Button } from '$lib/components/ui/button';
    import { cn } from '$lib/utils';

    interface Props {
        message: string;
        /** The user stopped the reply, so the turn did not fail. */
        isStopped: boolean;
        /** Retry and Edit are offered only for a turn that ended without an answer. */
        canResend: boolean;
        disabled: boolean;
        onRetry: () => void;
        onEdit: () => void;
    }

    const { message, isStopped, canResend, disabled, onRetry, onEdit }: Props = $props();
    const Icon = $derived(isStopped ? CircleStop : CircleAlert);
</script>

<div
    class={cn(
        'flex min-w-0 items-start gap-2 rounded-lg border px-3 py-2 text-xs',
        isStopped
            ? 'border-border/70 text-muted-foreground'
            : 'border-destructive/30 bg-destructive/5'
    )}
    role={isStopped ? 'status' : 'alert'}
>
    <Icon
        class={cn('mt-0.5 size-3.5 shrink-0', !isStopped && 'text-destructive')}
        aria-hidden="true"
    />
    <div class="min-w-0 flex-1 break-words">
        {message}
        {#if canResend}
            <div class="flex gap-3 pt-1">
                <Button
                    variant="link"
                    class="h-auto px-0 py-0 text-xs"
                    {disabled}
                    onclick={onRetry}
                >
                    Retry
                </Button>
                <Button variant="link" class="h-auto px-0 py-0 text-xs" onclick={onEdit}>
                    Edit message
                </Button>
            </div>
        {/if}
    </div>
</div>
