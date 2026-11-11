<script lang="ts">
    import { Button } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { PanelRightClose, PanelRightOpen } from '@lucide/svelte';

    const { isSampleDetailsSidePanelCollapsed, toggleSampleDetailsSidePanelCollapsed } =
        useGlobalStorage();

    const isCollapsed = $derived($isSampleDetailsSidePanelCollapsed);
    const label = $derived(isCollapsed ? 'Show side panel' : 'Hide side panel');
</script>

<Tooltip content={label} position="bottom" noTriggerRole>
    <Button
        icon={isCollapsed ? PanelRightOpen : PanelRightClose}
        variant="ghost"
        ariaLabel={label}
        buttonProps={{
            onclick: toggleSampleDetailsSidePanelCollapsed,
            'aria-expanded': !isCollapsed,
            'data-testid': 'side-panel-toggle',
            class: 'h-8 px-2'
        }}
    />
</Tooltip>
