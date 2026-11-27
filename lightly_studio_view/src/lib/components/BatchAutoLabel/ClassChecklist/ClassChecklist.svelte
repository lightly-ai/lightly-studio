<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';

    interface Props {
        classNames: string[];
        excluded: Set<string>;
        onExcludedChange: (excluded: Set<string>) => void;
    }

    let { classNames, excluded, onExcludedChange }: Props = $props();

    const toggle = (className: string, isChecked: boolean) => {
        const others = [...excluded].filter((name) => name !== className);
        onExcludedChange(new Set(isChecked ? others : [...others, className]));
    };
</script>

<div class="flex items-center justify-between text-xs text-muted-foreground">
    <span>Classes to save · {classNames.length - excluded.size} of {classNames.length}</span>
    <span class="flex gap-2">
        <button class="hover:text-foreground" onclick={() => onExcludedChange(new Set())}>
            All
        </button>
        <button class="hover:text-foreground" onclick={() => onExcludedChange(new Set(classNames))}>
            None
        </button>
    </span>
</div>
<div class="grid max-h-48 grid-cols-2 gap-x-3 gap-y-1 overflow-y-auto rounded-md border p-2">
    {#each classNames as className (className)}
        <label class="flex items-center gap-2 text-sm">
            <Checkbox
                checked={!excluded.has(className)}
                onCheckedChange={(isChecked) => toggle(className, isChecked)}
            />
            {className}
        </label>
    {/each}
</div>
