<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Select, type SelectItem } from '$lib/components/Select';

    type Strategy = 'diversity' | 'typicality' | 'similarity' | 'class_balancing' | '';

    interface Props {
        value: Strategy;
        isSimilaritySupported: boolean;
        onValueChange: (value: Strategy) => void;
    }

    let { value, isSimilaritySupported, onValueChange }: Props = $props();

    const items = $derived<SelectItem[]>([
        { value: 'diversity', label: 'Diversity', testId: 'sampling-strategy-diversity' },
        { value: 'typicality', label: 'Typicality', testId: 'sampling-strategy-typicality' },
        {
            value: 'class_balancing',
            label: 'Class Balancing',
            testId: 'sampling-strategy-class-balancing'
        },
        {
            value: 'similarity',
            label: 'Similarity',
            testId: 'sampling-strategy-similarity',
            disabled: !isSimilaritySupported
        }
    ]);
</script>

<div class="grid grid-cols-4 items-center gap-4">
    <Label for="strategy" class="text-right text-foreground">Strategy</Label>
    <Select
        {items}
        {value}
        placeholder="Select strategy"
        class="col-span-3"
        testId="sampling-dialog-strategy-select"
        onValueChange={(v) => onValueChange(v as Strategy)}
    />
</div>
