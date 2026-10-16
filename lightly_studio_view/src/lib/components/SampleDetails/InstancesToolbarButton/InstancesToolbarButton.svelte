<script lang="ts">
    import { Layers3 } from '@lucide/svelte';
    import { cn } from '$lib/utils';

    interface Props {
        onclick: () => void;
        isActive?: boolean;
        disabled?: boolean;
    }

    let { onclick, isActive = false, disabled = false }: Props = $props();
</script>

<!-- aria-disabled instead of disabled, so the tooltip with the reason still opens. -->
<button
    type="button"
    onclick={() => !disabled && onclick()}
    aria-label="Find all instances"
    aria-pressed={isActive}
    aria-disabled={disabled}
    class={cn(
        'flex items-center justify-center rounded-md p-2 transition-colors',
        isActive ? 'bg-black/40' : 'hover:bg-black/20',
        disabled && 'cursor-not-allowed opacity-50 hover:bg-transparent'
    )}
>
    <Layers3 class={cn('size-4', isActive && 'text-primary')} />
</button>
