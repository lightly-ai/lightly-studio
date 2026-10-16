<script lang="ts">
    import { SampleDetailsToolbarTooltip } from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip';
    import type { ToolbarStatus } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { useAssistedLabelingProvider } from '$lib/hooks/useAssistedLabelingProvider';
    import FindInstancesToolbarButton from '$lib/components/SampleDetails/FindInstancesToolbarButton/FindInstancesToolbarButton.svelte';
    import SmartSelectToolbarButton from '$lib/components/SampleDetails/SmartSelectToolbarButton/SmartSelectToolbarButton.svelte';

    interface Props {
        status: ToolbarStatus;
        onActivate: (status: 'smart-select' | 'find-instances') => void;
    }

    let { status, onActivate }: Props = $props();

    const provider = useAssistedLabelingProvider();
    const smartSelectReason = $derived(provider.tools.smartSelectDisabledReason);
    const instancesReason = $derived(provider.tools.instancesDisabledReason);
</script>

<SampleDetailsToolbarTooltip
    label="Smart select"
    hint={smartSelectReason ?? 'Segments the object that you click or box'}
>
    <SmartSelectToolbarButton
        onclick={() => onActivate('smart-select')}
        isActive={status === 'smart-select'}
        disabled={smartSelectReason !== null}
    />
</SampleDetailsToolbarTooltip>
<SampleDetailsToolbarTooltip
    label="Find all instances"
    hint={instancesReason ?? 'Finds all objects that match a text prompt'}
>
    <FindInstancesToolbarButton
        onclick={() => onActivate('find-instances')}
        isActive={status === 'find-instances'}
        disabled={instancesReason !== null}
    />
</SampleDetailsToolbarTooltip>
