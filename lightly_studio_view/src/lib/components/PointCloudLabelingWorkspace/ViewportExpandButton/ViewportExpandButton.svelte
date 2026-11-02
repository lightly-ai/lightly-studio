<script lang="ts">
    import { Maximize2, Minimize2 } from '@lucide/svelte';
    import { Button } from '$lib/components';

    /** Inputs and callbacks for viewport expand button. */
    interface Props {
        /** Whether this viewport occupies the full scene area. */
        expanded: boolean;
        /** Human-readable name of the view. */
        label: string;
        /** Expands this viewport or restores the multi-view layout. */
        onToggle: () => void;
    }

    let { expanded, label, onToggle }: Props = $props();
    const title = $derived(expanded ? 'Restore views' : `Expand ${label} view`);
</script>

<Button
    icon={expanded ? Minimize2 : Maximize2}
    ariaLabel={title}
    onclick={onToggle}
    buttonProps={{ type: 'button', size: 'icon', class: 'size-6 bg-background/80', title }}
/>
