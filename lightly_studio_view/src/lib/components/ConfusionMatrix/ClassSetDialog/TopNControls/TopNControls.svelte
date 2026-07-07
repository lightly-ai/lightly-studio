<script lang="ts">
    import { Select, type SelectItem } from '$lib/components/Select';
    import { Input } from '$lib/components/ui/input';
    import { CLASS_SORT_LABELS, type ClassSortOption } from '../../topNMatrix';
    import type { ClassSetConfig } from '../types';

    interface Props extends Pick<ClassSetConfig, 'n' | 'sortBy'> {
        /** Upper bound for the input, typically the total number of real classes in the matrix. */
        maxN: number;
    }

    let { n = $bindable(), sortBy = $bindable(), maxN }: Props = $props();

    const sortItems: SelectItem[] = (Object.keys(CLASS_SORT_LABELS) as ClassSortOption[]).map(
        (value) => ({ value, label: CLASS_SORT_LABELS[value] })
    );
</script>

<div class="space-y-3 pt-2">
    <label class="flex items-center justify-between gap-2 text-sm">
        Number of classes
        <Input
            type="number"
            min={1}
            max={maxN}
            bind:value={n}
            class="h-8 w-24"
            data-testid="class-set-top-n"
        />
    </label>
    <label class="flex items-center justify-between gap-2 text-sm">
        Sort by
        <Select
            items={sortItems}
            value={sortBy}
            size="xs"
            class="w-44"
            testId="class-set-sort-by"
            onValueChange={(value) => (sortBy = value as ClassSortOption)}
        />
    </label>
</div>
