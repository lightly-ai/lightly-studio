<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Select, SelectContent, SelectItem, SelectTrigger } from '$lib/components/ui/select';
    import { Switch } from '$lib/components/ui/switch';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import {
        createSettingsDialogFormState,
        createSettingsSavePayload,
        normalizeShortcutKey
    } from './settingsDialogState';
    import { shortcutSettings, staticShortcuts } from './settingsDialogConfig';
    import type { ShortcutSettingKey } from './settingsDialogConfig';
    import ShortcutSettingRow from './ShortcutSettingRow/ShortcutSettingRow.svelte';
    import SettingsFieldRow from './SettingsFieldRow/SettingsFieldRow.svelte';

    type SettingsDialogFormState = ReturnType<typeof createSettingsDialogFormState>;
    type RenderingMode = SettingsDialogFormState['gridViewRendering'];
    type ThumbnailQualityMode = SettingsDialogFormState['gridViewThumbnailQuality'];

    // Get settings from the store
    const { settingsStore, isLoadedStore, saveSettings } = useSettings();

    const { isSettingsDialogOpen, openSettingsDialog, closeSettingsDialog } = useSettingsDialog();
    let isSaving = $state(false);

    const initialFormState = createSettingsDialogFormState($settingsStore);
    let shortcuts = $state(initialFormState.shortcutSettings);
    let gridViewRendering: RenderingMode = $state(initialFormState.gridViewRendering);
    let gridViewThumbnailQuality: ThumbnailQualityMode = $state(
        initialFormState.gridViewThumbnailQuality
    );
    let showAnnotationTextLabels = $state<boolean>(initialFormState.showAnnotationTextLabels);
    let showSampleFilenames = $state<boolean>(initialFormState.showSampleFilenames);
    let showBoundingBoxesForSegmentation = $state<boolean>(
        initialFormState.showBoundingBoxesForSegmentation
    );

    let initialized = false;

    // Update local state when store changes
    $effect(() => {
        if ($settingsStore && $isLoadedStore && !initialized) {
            const formState = createSettingsDialogFormState($settingsStore);
            shortcuts = formState.shortcutSettings;
            gridViewRendering = formState.gridViewRendering;
            gridViewThumbnailQuality = formState.gridViewThumbnailQuality;
            showAnnotationTextLabels = formState.showAnnotationTextLabels;
            showSampleFilenames = formState.showSampleFilenames;
            showBoundingBoxesForSegmentation = formState.showBoundingBoxesForSegmentation;
            initialized = true;
        }
    });

    let recordingShortcut: ShortcutSettingKey | null = $state(null);

    function setOpen(isOpen: boolean) {
        if (isOpen) {
            openSettingsDialog();
        } else {
            closeSettingsDialog();
            recordingShortcut = null;
        }
    }

    function handleGridViewRenderingChange(value: string) {
        gridViewRendering = value as RenderingMode;
    }

    function handleGridViewThumbnailQualityChange(value: string) {
        gridViewThumbnailQuality = value as ThumbnailQualityMode;
    }

    // Submit handler
    function handleFormSubmit(event: Event) {
        event.preventDefault();
        submitSettings();
    }

    // Save settings
    async function submitSettings() {
        isSaving = true;

        try {
            await saveSettings(
                createSettingsSavePayload({
                    shortcutSettings: shortcuts,
                    gridViewRendering,
                    gridViewThumbnailQuality,
                    showAnnotationTextLabels,
                    showSampleFilenames,
                    showBoundingBoxesForSegmentation
                })
            );

            setOpen(false);
        } catch (error) {
            console.error('Error saving settings:', error);
        } finally {
            isSaving = false;
        }
    }

    // Start recording a keyboard shortcut
    const startRecording = (shortcutName: ShortcutSettingKey) => {
        recordingShortcut = shortcutName;
    };

    // Handle keyboard input when recording shortcuts
    const handleKeyDown = (event: KeyboardEvent) => {
        if (!recordingShortcut) return;

        // Prevent default and stop propagation to avoid triggering other shortcuts
        event.preventDefault();
        event.stopPropagation();

        shortcuts[recordingShortcut] = normalizeShortcutKey(event);

        // Stop recording
        recordingShortcut = null;
    };
</script>

<svelte:window onkeydown={handleKeyDown} />

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
                                value={shortcuts[setting.key]}
                                isRecording={recordingShortcut === setting.key}
                                onStartRecording={() => startRecording(setting.key)}
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
                                    value={gridViewRendering}
                                    onValueChange={handleGridViewRenderingChange}
                                >
                                    <SelectTrigger id="grid-view-rendering">
                                        {gridViewRendering === 'cover' ? 'Cover' : 'Contain'}
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
                                bind:checked={showSampleFilenames}
                                disabled={isSaving}
                            />
                        </SettingsFieldRow>
                        <SettingsFieldRow
                            id="grid-view-thumbnail-quality"
                            label="Thumbnail Quality in Grid View"
                        >
                            <div class="relative">
                                <Select
                                    type="single"
                                    value={gridViewThumbnailQuality}
                                    onValueChange={handleGridViewThumbnailQualityChange}
                                >
                                    <SelectTrigger id="grid-view-thumbnail-quality">
                                        {gridViewThumbnailQuality === 'high' ? 'High' : 'Original'}
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
                                bind:checked={showBoundingBoxesForSegmentation}
                                disabled={isSaving}
                            />
                        </SettingsFieldRow>
                        <SettingsFieldRow
                            id="show-annotation-text-labels"
                            label="Show Annotation Text Labels"
                        >
                            <Switch
                                id="show-annotation-text-labels"
                                bind:checked={showAnnotationTextLabels}
                                disabled={isSaving}
                            />
                        </SettingsFieldRow>
                    </div>
                </div>

                <Dialog.Footer>
                    <Button variant="outline" type="button" onclick={() => setOpen(false)}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={isSaving}>
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
