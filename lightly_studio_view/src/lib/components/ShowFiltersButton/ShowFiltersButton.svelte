<script lang="ts">
    import { Button } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { PanelLeftOpen } from '@lucide/svelte';

    const { toggleFilterPanelCollapsed } = useGlobalStorage();
</script>

<Button
    icon={PanelLeftOpen}
    variant="ghost"
    ariaLabel="Show filters"
    buttonProps={{
        onclick: toggleFilterPanelCollapsed,
        'aria-expanded': false,
        'data-testid': 'filter-panel-expand',
        class: 'h-8 gap-1.5 px-2 text-xs'
    }}
>
    Filters
</Button>
