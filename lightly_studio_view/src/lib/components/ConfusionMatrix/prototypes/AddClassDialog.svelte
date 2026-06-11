<script lang="ts">
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Dialog from '$lib/components/ui/dialog/index.js';

    interface Props {
        open: boolean;
        /** Classes available to add (not currently visible). */
        classes: string[];
        onAdd: (className: string) => void;
    }

    let { open = $bindable(), classes, onAdd }: Props = $props();

    const handleSelect = (className: string) => {
        onAdd(className);
        open = false;
    };
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="max-w-[360px]">
        <Dialog.Header>
            <Dialog.Title>Add class</Dialog.Title>
            <Dialog.Description>Type to find a class to add to the matrix.</Dialog.Description>
        </Dialog.Header>
        <Command.Root class="rounded-md border">
            <Command.Input placeholder="Search classes..." data-testid="add-class-input" />
            <Command.List class="max-h-[260px] dark:[color-scheme:dark]">
                <Command.Empty>No class found.</Command.Empty>
                {#each classes as className (className)}
                    <Command.Item value={className} onSelect={() => handleSelect(className)}>
                        {className}
                    </Command.Item>
                {/each}
            </Command.List>
        </Command.Root>
    </Dialog.Content>
</Dialog.Root>
