<script lang="ts">
    import { ChevronDown } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import * as Popover from '$lib/components/ui/popover';

    interface Props {
        fields: string[];
        onAdd: (field: string) => void;
    }

    const { fields, onAdd }: Props = $props();
    let open = $state(false);

    const addField = (field: string): void => {
        onAdd(field);
        open = false;
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                variant="outline"
                iconAfter={ChevronDown}
                iconAfterClass="opacity-50"
                disabledReason={fields.length === 0
                    ? 'No categorical metadata fields available to add.'
                    : ''}
                buttonProps={{
                    ...props,
                    size: 'sm',
                    class: 'h-10 w-full justify-between px-3 text-sm font-normal'
                }}
            >
                Add categorical metadata field
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="max-h-64 w-64 overflow-y-auto p-1" align="start">
        {#each fields as field (field)}
            <Button
                variant="ghost"
                buttonProps={{
                    size: 'sm',
                    class: 'w-full justify-start text-xs',
                    onclick: () => addField(field)
                }}
            >
                {field}
            </Button>
        {/each}
    </Popover.Content>
</Popover.Root>
