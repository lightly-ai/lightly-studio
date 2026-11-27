<script lang="ts">
    import CircleAlert from '@lucide/svelte/icons/circle-alert';
    import LoaderCircle from '@lucide/svelte/icons/loader-circle';
    import Wrench from '@lucide/svelte/icons/wrench';
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        name: string;
        status: 'running' | 'done' | 'error';
        summary: string;
    }

    const { name, status, summary }: Props = $props();

    const Icon = $derived(
        status === 'running' ? LoaderCircle : status === 'error' ? CircleAlert : Wrench
    );
</script>

<div
    class={cn(
        'flex items-center gap-1.5 self-start rounded-md bg-muted px-2 py-1 text-xs',
        status === 'error' ? 'text-destructive' : 'text-muted-foreground'
    )}
    data-testid="agent-chat-tool"
    data-status={status}
>
    <Icon class={cn('size-3 shrink-0', status === 'running' && 'animate-spin')} />
    <span class="font-mono">{name}</span>
    <span>·</span>
    <span>{summary}</span>
</div>
