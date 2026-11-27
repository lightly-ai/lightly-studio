<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Settings2 from '@lucide/svelte/icons/settings-2';
    import { Button } from '$lib/components';
    import WorkspacePanel from './WorkspacePanel.svelte';

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/WorkspacePanel',
        component: WorkspacePanel,
        tags: ['autodocs'],
        parameters: { layout: 'fullscreen' }
    });
</script>

{#snippet settings()}
    <Button
        variant="outline"
        icon={Settings2}
        buttonProps={{ type: 'button', size: 'xs', class: 'h-7 gap-1 px-2 text-xs' }}
    >
        Settings
    </Button>
{/snippet}

{#snippet placeholder(label: string)}
    <div class="flex h-full min-h-16 items-center justify-center bg-muted/40 text-xs">
        {label}
    </div>
{/snippet}

<Story name="Panel with settings">
    <div class="flex h-80 flex-col justify-end p-4">
        <WorkspacePanel
            title="Camera projections"
            onHide={() => {}}
            actions={settings}
            class="h-48"
        >
            {@render placeholder('Camera images')}
        </WorkspacePanel>
    </div>
</Story>
