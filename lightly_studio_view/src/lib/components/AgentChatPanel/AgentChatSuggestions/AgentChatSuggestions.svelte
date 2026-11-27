<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import type { Suggestion } from './suggestions';

    interface Props {
        suggestions: Suggestion[];
        disabled?: boolean;
        onPick: (prompt: string) => void;
    }

    const { suggestions, disabled = false, onPick }: Props = $props();
</script>

<div class="flex flex-wrap gap-2" data-testid="agent-chat-suggestions">
    <!-- The model writes the labels, so two labels can be equal. -->
    {#each suggestions as suggestion, index (index)}
        <Button
            variant="outline"
            size="sm"
            {disabled}
            class="h-auto max-w-full whitespace-normal break-words rounded-full px-3 py-1 text-left text-xs"
            onclick={() => onPick(suggestion.prompt)}
        >
            {suggestion.label}
        </Button>
    {/each}
</div>
