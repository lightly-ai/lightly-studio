<script lang="ts">
    import { ChevronDown } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import type { ChannelSummaryView } from '$lib/api/lightly_studio_local/types.gen';

    interface Props {
        /** Lane label shown in the trigger, e.g. "Lidar". */
        label: string;
        /** Channels offered in this lane. */
        channels: ChannelSummaryView[];
        /** `channel_id`s currently shown. */
        selectedChannels: number[];
        /** Toggles a channel on or off by its `channel_id`. */
        onToggleChannel: (channelId: number) => void;
        /** `data-testid` for the trigger; list items derive from it. */
        testId: string;
    }

    let { label, channels, selectedChannels, onToggleChannel, testId }: Props = $props();

    let open = $state(false);

    const items = $derived(
        channels.map((channel) => ({
            value: String(channel.channel_id),
            label: channel.group_component_name,
            testId: `${testId}-${channel.channel_id}`
        }))
    );
    const selectedIds = $derived(selectedChannels.map(String));

    const triggerLabel = $derived.by(() => {
        if (selectedChannels.length === 0) return label;
        if (selectedChannels.length === 1) {
            const only = channels.find((channel) => channel.channel_id === selectedChannels[0]);
            return only ? `${label}: ${only.group_component_name}` : label;
        }
        return `${label}: ${selectedChannels.length} selected`;
    });

    // MultiSelectList reports the full new selection; a single click only ever flips one id, so
    // relay it back through the toggle contract.
    const handleChange = (ids: string[]) => {
        const before = new Set(selectedIds);
        const toggled =
            ids.find((id) => !before.has(id)) ?? selectedIds.find((id) => !ids.includes(id));
        if (toggled !== undefined) onToggleChannel(Number(toggled));
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="sm"
                class="m-0 h-8 w-56 min-w-0 justify-start gap-2 rounded-md px-3 text-xs font-normal"
                role="combobox"
                aria-expanded={open}
                disabled={channels.length === 0}
                data-testid={testId}
            >
                <span class="truncate">{triggerLabel}</span>
                <ChevronDown class="ml-auto size-4 shrink-0 opacity-50" />
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-56 p-0 pt-2">
        <MultiSelectList
            {items}
            {selectedIds}
            onChange={handleChange}
            itemNoun="channel"
            itemNounPlural="channels"
        />
    </Popover.Content>
</Popover.Root>
