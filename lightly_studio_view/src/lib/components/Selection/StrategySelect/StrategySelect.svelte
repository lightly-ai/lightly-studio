<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';

    type Strategy = 'diversity' | 'typicality' | 'similarity' | 'class_balancing' | '';

    interface Props {
        value: Strategy;
        isSimilaritySupported: boolean;
        onValueChange: (value: Strategy) => void;
    }

    const STRATEGY_LABELS: Record<string, string> = {
        diversity: 'Diversity',
        typicality: 'Typicality',
        similarity: 'Similarity',
        class_balancing: 'Class Balancing'
    };

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
        <Select.Trigger class="col-span-3" data-testid="selection-dialog-strategy-select">
            {STRATEGY_LABELS[value] ?? 'Select strategy'}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                <Select.Item
                    value="diversity"
                    label="Diversity"
                    data-testid="selection-strategy-diversity">Diversity</Select.Item
                >
                <Select.Item
                    value="typicality"
                    label="Typicality"
                    data-testid="selection-strategy-typicality">Typicality</Select.Item
                >
                <Select.Item
                    value="class_balancing"
                    label="Class Balancing"
                    data-testid="selection-strategy-class-balancing">Class Balancing</Select.Item
                >
                <Select.Item
                    value="similarity"
                    label="Similarity"
                    data-testid="selection-strategy-similarity"
                    disabled={!isSimilaritySupported}>Similarity</Select.Item
                >
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
