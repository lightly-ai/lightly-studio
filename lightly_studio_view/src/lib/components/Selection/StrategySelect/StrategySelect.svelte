<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';

    type Strategy = 'diversity' | 'typicality' | 'similarity' | 'class_balancing' | '';

    interface Props {
        value: Strategy;
        isSimilaritySupported: boolean;
        onValueChange: (value: Strategy) => void;
    }

    const STRATEGIES: { value: Strategy; label: string; testId: string }[] = [
        { value: 'diversity', label: 'Diversity', testId: 'selection-strategy-diversity' },
        { value: 'typicality', label: 'Typicality', testId: 'selection-strategy-typicality' },
        {
            value: 'class_balancing',
            label: 'Class Balancing',
            testId: 'selection-strategy-class-balancing'
        },
        { value: 'similarity', label: 'Similarity', testId: 'selection-strategy-similarity' }
    ];

    const STRATEGY_LABELS = Object.fromEntries(STRATEGIES.map((s) => [s.value, s.label]));

    let { value, isSimilaritySupported, onValueChange }: Props = $props();
</script>

<div class="grid grid-cols-4 items-center gap-4">
    <Label for="strategy" class="text-right text-foreground">Strategy</Label>
    <Select.Root
        type="single"
        name="strategy"
        {value}
        onValueChange={(v) => onValueChange(v as Strategy)}
    >
        <Select.Trigger
            id="strategy"
            class="col-span-3"
            data-testid="selection-dialog-strategy-select"
        >
            {STRATEGY_LABELS[value] ?? 'Select strategy'}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                {#each STRATEGIES as strategy}
                    <Select.Item
                        value={strategy.value}
                        label={strategy.label}
                        data-testid={strategy.testId}
                        disabled={strategy.value === 'similarity' && !isSimilaritySupported}
                        >{strategy.label}</Select.Item
                    >
                {/each}
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
