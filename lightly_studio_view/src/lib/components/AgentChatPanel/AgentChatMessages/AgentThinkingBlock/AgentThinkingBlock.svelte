<script lang="ts">
    import Brain from '@lucide/svelte/icons/brain';
    import { cn } from '$lib/utils/shadcn';

    interface Props {
        text: string;
        /** The model writes the text now. A live block is open, a finished one is closed. */
        isLive: boolean;
    }

    const { text, isLive }: Props = $props();
</script>

<details
    class="max-w-[85%] self-start text-xs text-muted-foreground"
    open={isLive}
    data-testid="agent-chat-thinking-block"
>
    <summary class="flex cursor-pointer select-none items-center gap-1.5">
        <Brain class={cn('size-3 shrink-0', isLive && 'animate-pulse')} />
        <span>{isLive ? 'Thinking…' : 'Thought process'}</span>
    </summary>
    <p class="mt-1 whitespace-pre-wrap border-l-2 border-border pl-2">{text}</p>
</details>
