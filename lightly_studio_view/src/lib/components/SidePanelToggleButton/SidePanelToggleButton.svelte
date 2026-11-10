<script lang="ts">
    import { Button } from '$lib/components';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { PanelRightClose, PanelRightOpen } from '@lucide/svelte';

    const { isSampleDetailsSidePanelCollapsed, toggleSampleDetailsSidePanelCollapsed } =
        useGlobalStorage();

    const isCollapsed = $derived($isSampleDetailsSidePanelCollapsed);
</script>

<Button
    icon={isCollapsed ? PanelRightOpen : PanelRightClose}
    variant="ghost"
    ariaLabel={isCollapsed ? 'Show side panel' : 'Hide side panel'}
    buttonProps={{
        onclick: toggleSampleDetailsSidePanelCollapsed,
        'aria-expanded': !isCollapsed,
        'data-testid': 'side-panel-toggle',
        class: 'h-8 px-2'
    }}
/>
