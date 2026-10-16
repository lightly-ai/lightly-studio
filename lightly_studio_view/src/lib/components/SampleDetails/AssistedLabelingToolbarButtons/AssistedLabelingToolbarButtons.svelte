<script lang="ts">
    import { SampleDetailsToolbarTooltip } from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip';
    import type { ToolbarStatus } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { useAssistedLabelingProvider } from '$lib/hooks/useAssistedLabelingProvider';
    import SmartSelectToolbarButton from '$lib/components/SampleDetails/SmartSelectToolbarButton/SmartSelectToolbarButton.svelte';

    interface Props {
        status: ToolbarStatus;
        onActivate: (status: 'smart-select') => void;
    }

    let { status, onActivate }: Props = $props();

    const provider = useAssistedLabelingProvider();
    const smartSelectReason = $derived(provider.tools.smartSelectDisabledReason);
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
