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
        'data-testid': 'filter-panel-expand'
    }}
>
    Filters
</Button>
