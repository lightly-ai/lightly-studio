<script lang="ts">
    import { Select } from '$lib/components/Select';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { SettingsFieldRow } from '../SettingsFieldRow';
    import { SettingsGroup } from '../SettingsGroup';
    import { SettingsSwitchRow } from '../SettingsSwitchRow';

    interface Props {
        dialogState: Pick<
            SettingsDialogState,
            | 'showAnnotationTextLabels'
            | 'showBoundingBoxesForSegmentation'
            | 'annotationColorMode'
            | 'isSaving'
        >;
    }

    const { dialogState }: Props = $props();
</script>

<SettingsGroup title="Appearance">
    <SettingsFieldRow
        id="annotation-color-mode"
        label="Color by"
        description="Color annotations by annotation class or by annotation source."
    >
        <Select
            class="w-36"
            disabled={dialogState.isSaving}
            items={[
                { value: 'class', label: 'Class' },
                { value: 'source', label: 'Source' }
            ]}
            value={dialogState.annotationColorMode}
            selectProps={{ id: 'annotation-color-mode' }}
            onValueChange={(v) =>
                (dialogState.annotationColorMode = v as typeof dialogState.annotationColorMode)}
        />
    </SettingsFieldRow>
    <SettingsSwitchRow
        id="show-annotation-text-labels"
        label="Show annotation class names"
        description="Show the class name next to each annotation."
        bind:checked={dialogState.showAnnotationTextLabels}
        disabled={dialogState.isSaving}
    />
    <SettingsSwitchRow
        id="show-bounding-boxes-for-segmentation"
        label="Show bounding boxes for segmentation masks"
        description="Draw a bounding box around each segmentation mask."
        bind:checked={dialogState.showBoundingBoxesForSegmentation}
        disabled={dialogState.isSaving}
    />
</SettingsGroup>
