<script lang="ts">
    import { ClassSetConfigDialog } from '$lib/components/ClassSetConfig';
    import type { SelectItem } from '$lib/components/Select';
    import {
        DISTRIBUTION_SORT_LABELS,
        type DistributionConfig,
        type DistributionSortOption
    } from '../types';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Every class label available, used to bound top-N and populate the manual selector. */
        allClasses: string[];
        /** The currently applied config. */
        config: DistributionConfig;
        /** Invoked with the new config when the user clicks Apply. */
        onApply: (config: DistributionConfig) => void;
    }

    let { open = $bindable(), allClasses, config, onApply }: Props = $props();

    const sortItems: SelectItem[] = (
        Object.keys(DISTRIBUTION_SORT_LABELS) as DistributionSortOption[]
    ).map((value) => ({ value, label: DISTRIBUTION_SORT_LABELS[value] }));
</script>

<ClassSetConfigDialog
    bind:open
    {allClasses}
    selection={config}
    {sortItems}
    description="Choose which classes the distribution chart shows."
    testIdPrefix="distribution-config"
    showAllButton
    onApply={(selection) => onApply({ ...config, ...selection } as DistributionConfig)}
/>
