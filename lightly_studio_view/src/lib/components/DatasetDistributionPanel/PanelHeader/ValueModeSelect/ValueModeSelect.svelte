<script lang="ts">
    import { Select } from '$lib/components/Select';
    import type { ValueMode } from './types';

    const VALUE_MODE_ITEMS: { value: ValueMode; label: string }[] = [
        { value: 'number', label: 'Number' },
        { value: 'percentage', label: 'Percentage' }
    ];

    interface Props {
        value: ValueMode;
        testId?: string;
        onChange: (mode: ValueMode) => void;
    }

    const { value, testId, onChange }: Props = $props();
</script>

<Select
    items={VALUE_MODE_ITEMS}
    {value}
    size="xs"
    class="w-28"
    {testId}
    selectProps={{ 'aria-label': 'Distribution value mode' }}
    onValueChange={(v) => onChange(v as ValueMode)}
/>
