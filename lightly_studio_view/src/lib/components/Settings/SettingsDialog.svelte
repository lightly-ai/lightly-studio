<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Select, SelectContent, SelectItem, SelectTrigger } from '$lib/components/ui/select';
    import { Switch } from '$lib/components/ui/switch';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import { SettingsDialogState } from './settingsDialogState.svelte';
    import { shortcutSettings, staticShortcuts } from './settingsDialogConfig';
    import { ShortcutSettingRow } from './ShortcutSettingRow';
    import { SettingsFieldRow } from './SettingsFieldRow';

    const { settingsStore, saveSettings } = useSettings();
    const { isSettingsDialogOpen, openSettingsDialog, closeSettingsDialog } = useSettingsDialog();

    const dialogState = new SettingsDialogState();

    // Hydrate form state each time the dialog opens.
    let wasDialogOpen = false;
    $effect(() => {
        if ($isSettingsDialogOpen && !wasDialogOpen) {
            dialogState.hydrate($settingsStore);
        }
        wasDialogOpen = $isSettingsDialogOpen;
    });

    function setOpen(isOpen: boolean) {
        if (isOpen) {
            openSettingsDialog();
        } else {
            closeSettingsDialog();
            dialogState.clearRecording();
        }
    }

    async function handleFormSubmit(event: Event) {
        event.preventDefault();
        dialogState.isSaving = true;

        try {
            await saveSettings(dialogState.getSavePayload());
            setOpen(false);
        } catch (error) {
            console.error('Error saving settings:', error);
        } finally {
            dialogState.isSaving = false;
        }
    }
</script>

<svelte:window
    onkeydown={(e) => {
        if ($isSettingsDialogOpen) dialogState.handleKeyDown(e);
    }}
/>

<Dialog.Root open={$isSettingsDialogOpen} onOpenChange={(isOpen) => setOpen(isOpen)}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="max-h-[85vh] overflow-y-auto border-border bg-background dark:[color-scheme:dark] sm:max-w-[500px]"
        >
            <form onsubmit={handleFormSubmit}>
                <Dialog.Header>
                    <Dialog.Title class="text-foreground">Settings</Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        Configure your application preferences.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid gap-4 py-4">
                    <!-- Keyboard Shortcuts -->
                    <div class="space-y-4">
                        <h3 class="text-lg font-medium text-foreground">Keyboard Shortcuts</h3>
                        {#each shortcutSettings as setting (setting.id)}
                            <ShortcutSettingRow
                                id={setting.id}
                                label={setting.label}
                                value={dialogState.shortcuts[setting.key]}
                                isRecording={dialogState.recordingShortcut === setting.key}
                                onStartRecording={() => dialogState.startRecording(setting.key)}
                            />
                        {/each}
                        {#each staticShortcuts as setting (setting.id)}
                            <ShortcutSettingRow
                                id={setting.id}
                                label={setting.label}
                                value={setting.displayValue}
                                isRecording={false}
                                disabled
                            />
                        {/each}
                    </div>

                    <!-- Grid View Settings -->
                    <div class="space-y-4">
                        <h3 class="text-lg font-medium text-foreground">Display Settings</h3>
                        <SettingsFieldRow id="grid-view-rendering" label="Grid View Rendering">
                            <div class="relative">
                                <Select
                                    type="single"
                                    value={dialogState.gridViewRendering}
                                    onValueChange={(v) =>
                                        (dialogState.gridViewRendering =
                                            v as typeof dialogState.gridViewRendering)}
                                >
                                    <SelectTrigger id="grid-view-rendering">
                                        {dialogState.gridViewRendering === 'cover'
                                            ? 'Cover'
                                            : 'Contain'}
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="cover">Cover</SelectItem>
                                        <SelectItem value="contain">Contain</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </SettingsFieldRow>
                        <SettingsFieldRow
                            id="show-sample-filenames"
                            label="Show filenames in grid view"
                        >
                            <Switch
                                id="show-sample-filenames"
                                bind:checked={dialogState.showSampleFilenames}
                                disabled={dialogState.isSaving}
                            />
                        </SettingsFieldRow>
                        <SettingsFieldRow
                            id="grid-view-thumbnail-quality"
                            label="Thumbnail Quality in Grid View"
                        >
                            <div class="relative">
                                <Select
                                    type="single"
                                    value={dialogState.gridViewThumbnailQuality}
                                    onValueChange={(v) =>
                                        (dialogState.gridViewThumbnailQuality =
                                            v as typeof dialogState.gridViewThumbnailQuality)}
                                >
                                    <SelectTrigger id="grid-view-thumbnail-quality">
                                        {dialogState.gridViewThumbnailQuality === 'high'
                                            ? 'High'
                                            : 'Original'}
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="raw">Original</SelectItem>
                                        <SelectItem value="high">High</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </SettingsFieldRow>
                    </div>

                    <!-- Annotation Settings -->
                    <div class="space-y-4">
                        <h3 class="text-lg font-medium text-foreground">Annotation Settings</h3>
                        <SettingsFieldRow
                            id="show-bounding-boxes-for-segmentation"
                            label="Show Bounding Boxes for Segmentation"
                        >
                            <Switch
                                id="show-bounding-boxes-for-segmentation"
                                bind:checked={dialogState.showBoundingBoxesForSegmentation}
                                disabled={dialogState.isSaving}
                            />
                        </SettingsFieldRow>
                        <SettingsFieldRow
                            id="show-annotation-text-labels"
                            label="Show Annotation Text Labels"
                        >
                            <Switch
                                id="show-annotation-text-labels"
                                bind:checked={dialogState.showAnnotationTextLabels}
                                disabled={dialogState.isSaving}
                            />
                        </SettingsFieldRow>
                    </div>
                </div>

                <Dialog.Footer>
                    <Button variant="outline" type="button" onclick={() => setOpen(false)}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={dialogState.isSaving}>
                        {dialogState.isSaving ? 'Saving...' : 'Save Changes'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
