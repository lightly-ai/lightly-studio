<script lang="ts">
    import { Check, Palette } from '@lucide/svelte';
    import * as Popover from '$lib/components/ui/popover';
    import { Button } from '$lib/components/ui/button';
    import { useMetadataFilters } from '$lib/hooks';
    import { cn } from '$lib/utils';
    interface Props {
        collectionId: string;
        selectedKey: string | null;
        onSelectedKeyChange: (key: string | null) => void;
    }
    interface ChildProps {
        props: Record<string, unknown>;
    }
    const supportedTypes = new Set(['string', 'boolean']);
    let { collectionId, selectedKey, onSelectedKeyChange }: Props = $props();
    const { metadataInfo } = useMetadataFilters(collectionId);
    const colorableFields = $derived(
        ($metadataInfo ?? []).filter((field) => supportedTypes.has(field.type))
    );
    const buttonLabel = $derived(selectedKey ? `metadata.${selectedKey}` : 'Color by');
    const handleSelect = (key: string) => {
        onSelectedKeyChange(selectedKey === key ? null : key);
    };
</script>

<Popover.Root>
    <Popover.Trigger>
        {#snippet child({ props }: ChildProps)}
            <Button
                {...props}
                variant="outline"
                size="sm"
                class="gap-2 px-2.5"
                data-testid="plot-color-by-button"
            >
                <Palette class="h-4 w-4" />
                <span class="truncate">{buttonLabel}</span>
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-64 p-1" align="end">
        {#if colorableFields.length === 0}
            <div class="px-2 py-3 text-sm text-muted-foreground">Nothing to color by.</div>
        {:else}
            <div class="max-h-64 overflow-y-auto" data-testid="plot-color-by-options">
                {#each colorableFields as field (field.name)}
                    <button
                        type="button"
                        class={cn(
                            'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground',
                            selectedKey === field.name && 'bg-accent text-accent-foreground'
                        )}
                        onclick={() => handleSelect(field.name)}
                    >
                        <Check
                            class={cn(
                                'h-4 w-4 shrink-0',
                                selectedKey === field.name ? 'opacity-100' : 'opacity-0'
                            )}
                        />
                        <span class="truncate">{`metadata.${field.name}`}</span>
                    </button>
                {/each}
            </div>
        {/if}
    </Popover.Content>
</Popover.Root>
