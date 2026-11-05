<script lang="ts">
    import { ChevronDown } from '@lucide/svelte';
    import type { SequenceTrackView } from '$lib/api/lightly_studio_local/types.gen';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import { MultiSelectList } from '$lib/components/MultiSelectList';
    import { getTrackKey } from '../visibleTracks';

    /** Picks which tracks the timeline lists and always shows how many of them are listed. */
    interface Props {
        tracks: SequenceTrackView[];
        visibleCount: number;
        selectedKeys: string[];
        onChange: (keys: string[]) => void;
    }

    const { tracks, visibleCount, selectedKeys, onChange }: Props = $props();
    let open = $state(false);
    const items = $derived(
        tracks.map((track) => ({
            value: getTrackKey(track),
            label: `${track.annotation_label_name} · Track ${track.object_track_number}`
        }))
    );
    const existingKeys = $derived(
        selectedKeys.filter((key) => items.some((item) => item.value === key))
    );
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="sm"
                class="h-6 gap-1 px-2 text-xs font-normal"
                role="combobox"
                aria-expanded={open}
                data-testid="track-visibility-select"
            >
                Showing {visibleCount} of {tracks.length} tracks
                <ChevronDown class="size-3 opacity-50" />
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content class="w-[280px] p-0 pt-2">
        <MultiSelectList
            {items}
            selectedIds={existingKeys}
            {onChange}
            showSelectAll
            itemNoun="track"
            itemNounPlural="tracks"
        />
    </Popover.Content>
</Popover.Root>
