<script lang="ts">
    import { untrack, type ComponentProps } from 'svelte';
    import { SelectList } from '$lib/components/SelectList';
    import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';

    type ListItem = ComponentProps<typeof SelectList>['items'][number];

    const NO_TRACK_VALUE = '__no_track__';
    const NEW_TRACK_VALUE = '__new_track__';
    const NO_TRACK_LABEL = 'No track';
    const NEW_TRACK_LABEL = '+ New track';

    interface Props {
        tracks: TrackWithClassNameView[];
        value?: string;
        onValueChange?: (value: string | null, isNewTrack: boolean) => void;
    }

    let { tracks, value = $bindable(NO_TRACK_VALUE), onValueChange }: Props = $props();

    function trackLabel(t: TrackWithClassNameView): string {
        return t.annotation_class_name
            ? `${t.annotation_class_name} - ${t.object_track_number}`
            : `Track ${t.object_track_number}`;
    }

    const noTrackItem: ListItem = { value: NO_TRACK_LABEL, label: NO_TRACK_LABEL };
    const newTrackItem: ListItem = { value: NEW_TRACK_LABEL, label: NEW_TRACK_LABEL };

    const sortedItems = $derived.by(() => {
        return [...tracks]
            .sort((a, b) => {
                const classA = a.annotation_class_name ?? '';
                const classB = b.annotation_class_name ?? '';
                const cmp = classA.localeCompare(classB);
                if (cmp !== 0) return cmp;
                return a.object_track_number - b.object_track_number;
            })
            .map((t): ListItem => {
                const label = trackLabel(t);
                return { value: label, label };
            });
    });

    let selectedItem = $state<ListItem | undefined>({
        value: NO_TRACK_LABEL,
        label: NO_TRACK_LABEL
    });

    $effect(() => {
        let label: string;
        if (value === NO_TRACK_VALUE) {
            label = NO_TRACK_LABEL;
        } else if (value === NEW_TRACK_VALUE) {
            label = NEW_TRACK_LABEL;
        } else {
            const track = tracks.find((t) => t.object_track_id === value);
            label = track ? trackLabel(track) : NO_TRACK_LABEL;
        }
        if (untrack(() => selectedItem?.value) !== label) {
            selectedItem = { value: label, label };
        }
    });

    function handleSelect(item: ListItem) {
        if (item.value === NO_TRACK_LABEL) {
            value = NO_TRACK_VALUE;
            onValueChange?.(null, false);
        } else if (item.value === NEW_TRACK_LABEL) {
            value = NEW_TRACK_VALUE;
            onValueChange?.(null, true);
        } else {
            const track = tracks.find((t) => trackLabel(t) === item.value);
            if (track) {
                value = track.object_track_id;
                onValueChange?.(track.object_track_id, false);
            }
        }
    }
</script>

<div data-testid="track-select">
    <SelectList
        bind:selectedItem
        items={sortedItems}
        pinnedTop={[noTrackItem]}
        pinnedBottom={[newTrackItem]}
        label={NO_TRACK_LABEL}
        placeholder="Search track..."
        className="w-full"
        allowCreate={false}
        onSelect={handleSelect}
    />
</div>
