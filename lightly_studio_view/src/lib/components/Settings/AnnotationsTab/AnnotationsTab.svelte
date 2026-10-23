<script lang="ts">
    import { Switch } from '$lib/components/ui/switch';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { SettingsFieldRow } from '../SettingsFieldRow';
    import { SettingsGroup } from '../SettingsGroup';

    interface Props {
        dialogState: SettingsDialogState;
    }

    const { dialogState }: Props = $props();
</script>

<SettingsGroup title="Appearance">
    <SettingsFieldRow
        id="show-annotation-text-labels"
        label="Show annotation class names"
        description="Show the class name next to each annotation."
    >
        <Switch
            id="show-annotation-text-labels"
            bind:checked={dialogState.showAnnotationTextLabels}
            disabled={dialogState.isSaving}
        />
    </SettingsFieldRow>
    <SettingsFieldRow
        id="show-bounding-boxes-for-segmentation"
        label="Show bounding boxes for segmentation masks"
        description="Draw a bounding box around each segmentation mask."
    >
        <Switch
            id="show-bounding-boxes-for-segmentation"
            bind:checked={dialogState.showBoundingBoxesForSegmentation}
            disabled={dialogState.isSaving}
        />
    </SettingsFieldRow>
    <SettingsFieldRow
        id="enforce-coloring-by-class"
        label="Always color by class"
        description="Use class colors even when several annotation sources are visible."
    >
        <Switch
            id="enforce-coloring-by-class"
            bind:checked={dialogState.enforceColoringByClass}
            disabled={dialogState.isSaving}
        />
    </SettingsFieldRow>
</SettingsGroup>
