<script lang="ts">
    import { Check as CheckIcon, ChevronsUpDown as ChevronsUpDownIcon } from '@lucide/svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils';

    interface Props {
        /** Currently picked name, or an empty string when nothing is picked yet. */
        value: string;
        /** Names to choose from. */
        options: string[];
        /** Trigger text shown while `value` is empty. */
        placeholder: string;
        /** Search input placeholder. */
        searchPlaceholder: string;
        /** Accessible name of the trigger. */
        ariaLabel: string;
        onPick: (name: string) => void;
        disabled?: boolean;
        testId: string;
    }

    const {
        value,
        options,
        placeholder,
        searchPlaceholder,
        ariaLabel,
        onPick,
        disabled = false,
        testId
    }: Props = $props();

    let open = $state(false);
    let inputValue = $state('');
    let highlightedValue = $state('');

    $effect(() => {
        if (!open) {
            inputValue = '';
            highlightedValue = '';
        }
    });

    const typedName = $derived(inputValue.trim());
    const canCreate = $derived(typedName.length > 0 && !options.includes(typedName));

    const pick = (name: string) => {
        const trimmed = name.trim();
        if (!trimmed) return;
        onPick(trimmed);
        open = false;
    };

    // Mirror SelectList: Enter with no highlighted item takes the typed name.
    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter' && !highlightedValue && typedName) {
            pick(typedName);
            event.preventDefault();
            event.stopPropagation();
        }
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props }: { props: Record<string, unknown> })}
            <Button
                variant="secondary"
                {ariaLabel}
                buttonProps={{
                    ...props,
                    disabled,
                    class: 'w-full min-w-0 justify-between',
                    role: 'combobox',
                    'aria-expanded': open,
                    'data-testid': `${testId}-trigger`
                }}
            >
                <span class={cn('min-w-0 flex-1 truncate text-left', !value && 'opacity-60')}>
                    {value || placeholder}
                </span>
                <ChevronsUpDownIcon class="size-4 shrink-0 opacity-50" />
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-[var(--bits-popover-anchor-width)] p-0" align="start">
        <Command.Root bind:value={highlightedValue}>
            <Command.Input
                placeholder={searchPlaceholder}
                onkeydown={handleKeyDown}
                bind:value={inputValue}
                data-testid={`${testId}-input`}
            />
            <Command.List class="dark:[color-scheme:dark]">
                <Command.Group>
                    {#each options as name (name)}
                        <Command.Item
                            value={name}
                            onSelect={() => pick(name)}
                            data-testid={`${testId}-option-${name}`}
                        >
                            <CheckIcon class={cn(value !== name && 'text-transparent')} />
                            <span class="min-w-0 flex-1 truncate">{name}</span>
                        </Command.Item>
                    {/each}
                </Command.Group>
                {#if canCreate}
                    <div class="border-t">
                        <Command.Item
                            value="__create__"
                            onSelect={() => pick(typedName)}
                            forceMount
                            keywords={[]}
                            data-testid={`${testId}-create`}
                        >
                            <span class="opacity-50">Create:</span>
                            <span class="ml-1 min-w-0 flex-1 truncate font-semibold">
                                {typedName}
                            </span>
                        </Command.Item>
                    </div>
                {/if}
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
