<script lang="ts">
    import Eye from '@lucide/svelte/icons/eye';
    import EyeOff from '@lucide/svelte/icons/eye-off';
    import { Button } from '$lib/components/ui/button';
    import { Tooltip } from '$lib/components/ui/tooltip';

    interface Props {
        /** What the button hides, e.g. "annotation" or "source". */
        noun: string;
        isHidden: boolean;
        disabled?: boolean;
        onToggle: () => void;
    }

    let { noun, isHidden, disabled = false, onToggle }: Props = $props();

    const label = $derived(`${isHidden ? 'Show' : 'Hide'} ${noun}`);
</script>

<Tooltip content={label}>
    <Button
        variant="ghost"
        size="icon"
        class="h-7 w-7 shrink-0 text-muted-foreground"
        {disabled}
        onclick={onToggle}
        aria-label={label}
        data-testid="point-cloud-{noun}-visibility-button"
    >
        {#if isHidden}
            <EyeOff class="size-4 shrink-0" />
        {:else}
            <Eye class="size-4 shrink-0" />
        {/if}
    </Button>
</Tooltip>
