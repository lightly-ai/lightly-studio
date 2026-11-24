<script lang="ts">
    import { Button } from '$lib/components';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import PanelRightClose from '@lucide/svelte/icons/panel-right-close';
    import PanelRightOpen from '@lucide/svelte/icons/panel-right-open';

    const { isSampleDetailsSidePanelCollapsed, toggleSampleDetailsSidePanelCollapsed } =
        useGlobalStorage();

    const label = $derived(
        $isSampleDetailsSidePanelCollapsed ? 'Show side panel' : 'Hide side panel'
    );
</script>

<Tooltip content={label} position="bottom" noTriggerRole>
    <Button
        icon={$isSampleDetailsSidePanelCollapsed ? PanelRightOpen : PanelRightClose}
        variant="ghost"
        ariaLabel={label}
        buttonProps={{
            onclick: toggleSampleDetailsSidePanelCollapsed,
            'aria-expanded': !$isSampleDetailsSidePanelCollapsed,
            'data-testid': 'side-panel-toggle',
            class: 'h-8 px-2'
        }}
    />
</Tooltip>
