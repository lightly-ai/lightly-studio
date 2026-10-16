<script lang="ts">
    import { SampleDetailsToolbarTooltip } from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip';
    import type { ToolbarStatus } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { useAssistedLabelingProvider } from '$lib/hooks/useAssistedLabelingProvider';
    import InstancesToolbarButton from '../InstancesToolbarButton/InstancesToolbarButton.svelte';
    import WandToolbarButton from '../WandToolbarButton/WandToolbarButton.svelte';

    interface Props {
        status: ToolbarStatus;
        onActivate: (status: 'wand' | 'instances') => void;
    }

    let { status, onActivate }: Props = $props();

    const provider = useAssistedLabelingProvider();
    const smartSelectReason = $derived(provider.tools.smartSelectDisabledReason);
    const instancesReason = $derived(provider.tools.instancesDisabledReason);
</script>

<SampleDetailsToolbarTooltip
    label="Find all instances"
    hint={instancesReason ?? 'Finds all objects that match a text prompt'}
>
    <InstancesToolbarButton
        onclick={() => onActivate('instances')}
        isActive={status === 'instances'}
        disabled={instancesReason !== null}
    />
</SampleDetailsToolbarTooltip>
<SampleDetailsToolbarTooltip
    label="Smart select"
    hint={smartSelectReason ?? 'Segments the object that you click or box'}
>
    <WandToolbarButton
        onclick={() => onActivate('wand')}
        isActive={status === 'wand'}
        disabled={smartSelectReason !== null}
    />
</SampleDetailsToolbarTooltip>
