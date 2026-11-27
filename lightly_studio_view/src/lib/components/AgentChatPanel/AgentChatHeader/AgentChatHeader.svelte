<script lang="ts">
    import ArrowLeft from '@lucide/svelte/icons/arrow-left';
    import History from '@lucide/svelte/icons/history';
    import SquarePen from '@lucide/svelte/icons/square-pen';
    import Sparkles from '@lucide/svelte/icons/sparkles';
    import X from '@lucide/svelte/icons/x';
    import { Button } from '$lib/components/ui/button';

    interface Props {
        collectionName: string;
        showHistory: boolean;
        onToggleHistory: () => void;
        onNewChat: () => void;
        onClose: () => void;
    }

    const { collectionName, showHistory, onToggleHistory, onNewChat, onClose }: Props = $props();
</script>

<header class="flex shrink-0 items-center gap-3 border-b border-border/70 px-4 py-3.5">
    <div class="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
        <Sparkles class="size-4" aria-hidden="true" />
    </div>
    <div class="min-w-0 flex-1">
        <h2 class="text-sm font-semibold">AI Agent</h2>
        <p class="truncate text-xs text-muted-foreground" title={collectionName}>
            {collectionName}
        </p>
    </div>
    <div class="flex shrink-0 gap-0.5">
        <Button
            variant="ghost"
            size="icon"
            class="size-8"
            aria-label={showHistory ? 'Back to chat' : 'History'}
            title={showHistory ? 'Back to chat' : 'History'}
            aria-expanded={showHistory}
            onclick={onToggleHistory}
        >
            {#if showHistory}
                <ArrowLeft class="size-4" />
            {:else}
                <History class="size-4" />
            {/if}
        </Button>
        <Button
            variant="ghost"
            size="icon"
            class="size-8"
            aria-label="New chat"
            title="New chat"
            onclick={onNewChat}
        >
            <SquarePen class="size-4" />
        </Button>
        <Button
            variant="ghost"
            size="icon"
            class="size-8"
            aria-label="Close agent panel"
            title="Close agent panel"
            onclick={onClose}
        >
            <X class="size-4" />
        </Button>
    </div>
</header>
