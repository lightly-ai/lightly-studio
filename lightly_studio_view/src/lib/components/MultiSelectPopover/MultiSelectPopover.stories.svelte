<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import MultiSelectPopover from './MultiSelectPopover.svelte';

    const { Story } = defineMeta({
        title: 'Components/MultiSelectPopover',
        component: MultiSelectPopover,
        tags: ['autodocs'],
        args: {
            items: [],
            selectedIds: [],
            label: 'No tags',
            onChange: () => {},
            itemNoun: 'tag',
            itemNounPlural: 'tags'
        }
    });
</script>

<script lang="ts">
    const tags = [
        { value: 'cat', label: 'Cat' },
        { value: 'dog', label: 'Dog' },
        { value: 'elephant', label: 'Elephant' },
        { value: 'occluded', label: 'Occluded' },
        { value: 'night', label: 'Night' }
    ];
    const tracks = Array.from({ length: 14 }, (_, index) => ({
        value: `track-${index + 1}`,
        label: `Truck · Track ${index + 1}`
    }));

    let selectedTags = $state<string[]>(['cat', 'dog', 'elephant']);
    let selectedTracks = $state<string[]>(tracks.slice(0, 10).map((track) => track.value));
    let noneSelected = $state<string[]>([]);
</script>

<Story name="Tags" asChild>
    <MultiSelectPopover
        items={tags}
        selectedIds={selectedTags}
        onChange={(ids) => (selectedTags = ids)}
        label={`${selectedTags.length} tags selected`}
        itemNoun="tag"
        itemNounPlural="tags"
        showSelectAll
    />
</Story>

<Story name="Many tracks" asChild>
    <MultiSelectPopover
        items={tracks}
        selectedIds={selectedTracks}
        onChange={(ids) => (selectedTracks = ids)}
        label={`Showing ${selectedTracks.length} of ${tracks.length} tracks`}
        itemNoun="track"
        itemNounPlural="tracks"
        showSelectAll
        triggerClass="h-6 gap-1 px-2"
    />
</Story>

<Story name="Nothing selected" asChild>
    <MultiSelectPopover
        items={tags}
        selectedIds={noneSelected}
        onChange={(ids) => (noneSelected = ids)}
        label="Compare sample tags"
        itemNoun="tag"
        itemNounPlural="tags"
    />
</Story>

<Story name="Disabled" args={{ label: 'Lidar', disabled: true }} />
