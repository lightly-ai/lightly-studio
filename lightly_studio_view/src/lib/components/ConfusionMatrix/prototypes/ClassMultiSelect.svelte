<script lang="ts">
    import { Check as CheckIcon, ChevronsUpDown as ChevronsUpDownIcon } from '@lucide/svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Button } from '$lib/components/ui/button/index.js';
    import { cn } from '$lib/utils';

    interface Props {
        allClasses: string[];
        selected: string[];
        onToggle: (className: string) => void;
        label?: string;
    }

    const { allClasses, selected, onToggle, label = 'Edit classes' }: Props = $props();

    type ChildProps = {
        props: Record<string, unknown>;
    };

    let open = $state(false);
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props }: ChildProps)}
            <Button
                {...props}
                variant="outline"
                size="sm"
                role="combobox"
                aria-expanded={open}
                data-testid="class-multi-select-trigger"
            >
                {label}
                <ChevronsUpDownIcon class="shrink-0 opacity-50" />
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-[240px] p-0" align="end">
        <Command.Root>
            <Command.Input placeholder="Search classes..." />
            <Command.List class="max-h-[300px] dark:[color-scheme:dark]">
                <Command.Empty>No class found.</Command.Empty>
                <Command.Group>
                    {#each allClasses as className (className)}
                        <Command.Item value={className} onSelect={() => onToggle(className)}>
                            <CheckIcon
                                class={cn(!selected.includes(className) && 'text-transparent')}
                            />
                            <span class="min-w-0 flex-1 truncate">{className}</span>
                        </Command.Item>
                    {/each}
                </Command.Group>
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
