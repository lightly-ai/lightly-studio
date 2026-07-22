<script lang="ts">
    import { Check as CheckIcon } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Command from '$lib/components/ui/command';
    import { cn } from '$lib/utils';

    interface Props {
        /** Currently selected class labels. Bindable — mutated on toggle / Select all / Clear. */
        selected: string[];
        /** Full list of class labels to choose from, in the order they should be displayed. */
        allClasses: string[];
        /** test-id for the search input; lets each host keep its own id scheme. */
        searchTestId?: string;
    }

    let { selected = $bindable(), allClasses, searchTestId }: Props = $props();

    const toggle = (className: string) => {
        selected = selected.includes(className)
            ? selected.filter((c) => c !== className)
            : [...selected, className];
    };
</script>

<div class="pt-2">
    <div class="mb-1 flex items-center justify-between">
        <span class="text-xs text-muted-foreground">
            {selected.length} of {allClasses.length} selected
        </span>
        <div class="flex gap-1">
            <Button
                variant="ghost"
                size="sm"
                class="h-6 px-2 text-xs"
                onclick={() => (selected = [...allClasses])}
            >
                Select all
            </Button>
            <Button
                variant="ghost"
                size="sm"
                class="h-6 px-2 text-xs"
                onclick={() => (selected = [])}
            >
                Clear
            </Button>
        </div>
    </div>
    <Command.Root class="rounded-md border">
        <Command.Input placeholder="Search classes..." data-testid={searchTestId} />
        <Command.List class="max-h-[220px] dark:[color-scheme:dark]">
            <Command.Empty>No class found.</Command.Empty>
            {#each allClasses as className (className)}
                <Command.Item value={className} onSelect={() => toggle(className)}>
                    <CheckIcon class={cn(!selected.includes(className) && 'text-transparent')} />
                    <span class="min-w-0 flex-1 truncate">{className}</span>
                </Command.Item>
            {/each}
        </Command.List>
    </Command.Root>
</div>
