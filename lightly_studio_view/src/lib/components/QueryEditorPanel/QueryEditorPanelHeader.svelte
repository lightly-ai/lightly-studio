<script lang="ts">
    import X from '@lucide/svelte/icons/x';
    import { Button } from '$lib/components';
    import Typography from '$lib/components/Typography/Typography.svelte';

    import QuerySyntaxHelp from './QuerySyntaxHelp.svelte';

    interface Props {
        sampleType: 'image' | 'video';
        onClose: () => void;
    }

    const { sampleType, onClose }: Props = $props();
</script>

<div class="mb-3 min-w-0">
    <div class="flex items-center justify-between">
        <Typography variant="h5" component="h2" className="text-foreground">Query Filter</Typography
        >
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
    </div>
    <QuerySyntaxHelp {sampleType} />
</div>
