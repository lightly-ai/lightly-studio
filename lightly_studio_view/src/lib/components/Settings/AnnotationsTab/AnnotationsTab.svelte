<script lang="ts">
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { SettingsGroup } from '../SettingsGroup';
    import { SettingsSwitchRow } from '../SettingsSwitchRow';

    interface Props {
        dialogState: Pick<
            SettingsDialogState,
            | 'showAnnotationTextLabels'
            | 'showBoundingBoxesForSegmentation'
            | 'enforceColoringByClass'
            | 'isSaving'
        >;
    }

    const { dialogState }: Props = $props();
</script>

<SettingsGroup title="Appearance">
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
    <SettingsSwitchRow
        id="enforce-coloring-by-class"
        label="Always color by class"
        description="Use class colors even when several annotation sources are visible."
        bind:checked={dialogState.enforceColoringByClass}
        disabled={dialogState.isSaving}
    />
</SettingsGroup>
