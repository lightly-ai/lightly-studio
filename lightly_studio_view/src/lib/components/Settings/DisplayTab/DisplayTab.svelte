<script lang="ts">
    import { Select } from '$lib/components/Select';
    import { Switch } from '$lib/components/ui/switch';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { SettingsFieldRow } from '../SettingsFieldRow';
    import { SettingsGroup } from '../SettingsGroup';

    interface Props {
        dialogState: Pick<
            SettingsDialogState,
            | 'gridViewRendering'
            | 'gridViewThumbnailQuality'
            | 'imageInterpolation'
            | 'showSampleFilenames'
            | 'isSaving'
        >;
    }

    const { dialogState }: Props = $props();
</script>

<div class="space-y-8">
    <SettingsGroup title="Grid view">
        <SettingsFieldRow
            id="grid-view-rendering"
            label="Image fit"
            description="Cover crops images to fill each cell. Contain shows the whole image."
        >
            <Select
                class="w-36"
                items={[
                    { value: 'cover', label: 'Cover' },
                    { value: 'contain', label: 'Contain' }
                ]}
                value={dialogState.gridViewRendering}
                selectProps={{ id: 'grid-view-rendering' }}
                onValueChange={(v) =>
                    (dialogState.gridViewRendering = v as typeof dialogState.gridViewRendering)}
            />
        </SettingsFieldRow>
        <SettingsFieldRow
            id="grid-view-thumbnail-quality"
            label="Thumbnail quality"
            description="High loads copies resized to the cell size. Original loads the full files."
        >
            <Select
                class="w-36"
                items={[
                    { value: 'raw', label: 'Original' },
                    { value: 'high', label: 'High' }
                ]}
                value={dialogState.gridViewThumbnailQuality}
                selectProps={{ id: 'grid-view-thumbnail-quality' }}
                onValueChange={(v) =>
                    (dialogState.gridViewThumbnailQuality =
                        v as typeof dialogState.gridViewThumbnailQuality)}
            />
        </SettingsFieldRow>
        <SettingsFieldRow
            id="show-sample-filenames"
            label="Show filenames"
            description="Show the filename with each sample in the grid."
            isLabelClickable
        >
            <Switch
                id="show-sample-filenames"
                bind:checked={dialogState.showSampleFilenames}
                disabled={dialogState.isSaving}
            />
        </SettingsFieldRow>
    </SettingsGroup>
    <SettingsGroup title="Images">
        <SettingsFieldRow
            id="image-interpolation"
            label="Image interpolation"
            description="Smooth images when they are scaled. Turn off to see individual pixels."
            isLabelClickable
        >
            <Switch
                id="image-interpolation"
                bind:checked={dialogState.imageInterpolation}
                disabled={dialogState.isSaving}
            />
        </SettingsFieldRow>
    </SettingsGroup>
</div>
