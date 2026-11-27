<script lang="ts">
    import X from '@lucide/svelte/icons/x';
    import { Button, PanelTitleBar } from '$lib/components';

    import QuerySyntaxHelp from './QuerySyntaxHelp.svelte';

    interface Props {
        sampleType: 'image' | 'video';
        onClose: () => void;
    }

    const { sampleType, onClose }: Props = $props();
</script>

<div class="mb-3 min-w-0">
    <PanelTitleBar title="Query Filter">
        {#snippet actions()}
            <Button
                icon={X}
                variant="ghost"
                ariaLabel="Close query filter panel"
                buttonProps={{
                    size: 'icon',
                    onclick: onClose,
                    class: 'h-8 w-8',
                    'data-testid': 'query-editor-close-button'
                }}
            />
        {/snippet}
    </PanelTitleBar>
    <QuerySyntaxHelp {sampleType} />
</div>
