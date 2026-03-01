<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Label } from '$lib/components/ui/label';
    import { Select, SelectContent, SelectItem, SelectTrigger } from '$lib/components/ui/select';
    import { Switch } from '$lib/components/ui/switch';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';

    // Get settings from the store
    const { settingsStore, isLoadedStore, saveSettings } = useSettings();

    const { isSettingsDialogOpen, openSettingsDialog, closeSettingsDialog } = useSettingsDialog();
    let isSaving = $state(false);

    // Initialize with default values first
    let shortcutSettings = $state({
        hideAnnotations: 'v',
        goBack: 'Escape',
        toggleEditMode: 'e',
        keyToolbarSelection: 's',
        keyToolbarDrag: $settingsStore.key_toolbar_drag,
        keyToolbarBoundingBox: $settingsStore.key_toolbar_bounding_box,
        keyToolbarSegmentationMask: $settingsStore.key_toolbar_segmentation_mask
    });
    type RenderingMode = 'contain' | 'cover';
    let gridViewRendering: RenderingMode = $state('contain');
    let showAnnotationTextLabels = $state<boolean>(true);
    let showSampleFilenames = $state<boolean>(false);

    let initialized = false;

    // Update local state when store changes
    $effect(() => {
        if ($settingsStore && $isLoadedStore && !initialized) {
            shortcutSettings = {
                hideAnnotations: $settingsStore.key_hide_annotations || 'v',
                goBack: $settingsStore.key_go_back || 'Escape',
                toggleEditMode: $settingsStore.key_toggle_edit_mode || 'e',
                keyToolbarSelection: $settingsStore.key_toolbar_selection,
                keyToolbarDrag: $settingsStore.key_toolbar_drag,
                keyToolbarBoundingBox: $settingsStore.key_toolbar_bounding_box,
                keyToolbarSegmentationMask: $settingsStore.key_toolbar_segmentation_mask
            };
            gridViewRendering = $settingsStore.grid_view_sample_rendering || 'contain';
            showAnnotationTextLabels = Boolean($settingsStore.show_annotation_text_labels ?? true);
            showSampleFilenames = Boolean($settingsStore.show_sample_filenames ?? false);
            initialized = true;
        }
    });

    let recordingShortcut: string | null = $state(null);

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

    // Submit handler
    function handleFormSubmit(event: Event) {
        event.preventDefault();
        submitSettings();
    }

    // Save settings
    async function submitSettings() {
        isSaving = true;

        try {
            await saveSettings({
                key_hide_annotations: shortcutSettings.hideAnnotations,
                key_go_back: shortcutSettings.goBack,
                key_toggle_edit_mode: shortcutSettings.toggleEditMode,
                grid_view_sample_rendering: gridViewRendering,
                show_annotation_text_labels: showAnnotationTextLabels,
                show_sample_filenames: showSampleFilenames,
                key_toolbar_selection: shortcutSettings.keyToolbarSelection,
                key_toolbar_drag: shortcutSettings.keyToolbarDrag,
                key_toolbar_bounding_box: shortcutSettings.keyToolbarBoundingBox,
                key_toolbar_segmentation_mask: shortcutSettings.keyToolbarSegmentationMask
            });

            setOpen(false);
        } catch (error) {
            console.error('Error saving settings:', error);
        } finally {
            isSaving = false;
        }
    }

    // Start recording a keyboard shortcut
    const startRecording = (shortcutName: string) => {
        recordingShortcut = shortcutName;
    };

    // Handle keyboard input when recording shortcuts
    const handleKeyDown = (event: KeyboardEvent) => {
        if (!recordingShortcut) return;

        // Prevent default and stop propagation to avoid triggering other shortcuts
        event.preventDefault();
        event.stopPropagation();

        // Get the key name
        let keyName = event.key;

        // Special handling for certain keys
        if (keyName === ' ') {
            keyName = 'Space';
        } else if (keyName.length === 1) {
            // For single character keys, keep the case as is (respect Caps Lock)
            // But for letters, prefer lowercase for better matching
            if (/^[a-zA-Z]$/.test(keyName) && !event.getModifierState('CapsLock')) {
                keyName = keyName.toLowerCase();
            }
        }

        // Update the shortcut setting
        if (recordingShortcut in shortcutSettings)
            shortcutSettings[recordingShortcut as keyof typeof shortcutSettings] = keyName;

        // Stop recording
        recordingShortcut = null;
    };
</script>

<svelte:window onkeydown={handleKeyDown} />

<Dialog.Root open={$isSettingsDialogOpen} onOpenChange={(isOpen) => setOpen(isOpen)}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="max-h-[85vh] overflow-y-scroll border-border bg-background sm:max-w-[500px]"
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
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="hide-annotations" class="text-right text-foreground">
                                Hide Annotations
                            </Label>
                            <button
                                id="hide-annotations"
                                type="button"
                                class="rounded-md border border-input bg-background p-2 text-left text-foreground"
                                onclick={(e) => {
                                    e.preventDefault();
                                    startRecording('hideAnnotations');
                                }}
                            >
                                {#if recordingShortcut === 'hideAnnotations'}
                                    <span class="italic opacity-70">Press a key...</span>
                                {:else}
                                    <span>{shortcutSettings.hideAnnotations}</span>
                                {/if}
                            </button>
                        </div>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="go-back" class="text-right text-foreground">Go Back</Label>
                            <button
                                id="go-back"
                                type="button"
                                class="rounded-md border border-input bg-background p-2 text-left text-foreground"
                                onclick={(e) => {
                                    e.preventDefault();
                                    startRecording('goBack');
                                }}
                            >
                                {#if recordingShortcut === 'goBack'}
                                    <span class="italic opacity-70">Press a key...</span>
                                {:else}
                                    <span>{shortcutSettings.goBack}</span>
                                {/if}
                            </button>
                        </div>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="toggle-edit-mode" class="text-right text-foreground">
                                Toggle Edit Mode
                            </Label>
                            <button
                                id="toggle-edit-mode"
                                type="button"
                                class="rounded-md border border-input bg-background p-2 text-left text-foreground"
                                onclick={(e) => {
                                    e.preventDefault();
                                    startRecording('toggleEditMode');
                                }}
                            >
                                {#if recordingShortcut === 'toggleEditMode'}
                                    <span class="italic opacity-70">Press a key...</span>
                                {:else}
                                    <span>{shortcutSettings.toggleEditMode}</span>
                                {/if}
                            </button>
                        </div>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="toggle-edit-mode" class="text-right text-foreground">
                                Toolbar selection
                            </Label>
                            <button
                                id="toggle-edit-mode"
                                type="button"
                                class="rounded-md border border-input bg-background p-2 text-left text-foreground"
                                onclick={(e) => {
                                    e.preventDefault();
                                    startRecording('keyToolbarSelection');
                                }}
                            >
                                {#if recordingShortcut === 'keyToolbarSelection'}
                                    <span class="italic opacity-70">Press a key...</span>
                                {:else}
                                    <span>{shortcutSettings.keyToolbarSelection}</span>
                                {/if}
                            </button>
                        </div>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="toggle-edit-mode" class="text-right text-foreground">
                                Toolbar drag
                            </Label>
                            <button
                                id="toggle-edit-mode"
                                type="button"
                                class="rounded-md border border-input bg-background p-2 text-left text-foreground"
                                onclick={(e) => {
                                    e.preventDefault();
                                    startRecording('keyToolbarDrag');
                                }}
                            >
                                {#if recordingShortcut === 'keyToolbarDrag'}
                                    <span class="italic opacity-70">Press a key...</span>
                                {:else}
                                    <span>{shortcutSettings.keyToolbarDrag}</span>
                                {/if}
                            </button>
                        </div>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="toggle-edit-mode" class="text-right text-foreground">
                                Toolbar bounding box
                            </Label>
                            <button
                                id="toggle-edit-mode"
                                type="button"
                                class="rounded-md border border-input bg-background p-2 text-left text-foreground"
                                onclick={(e) => {
                                    e.preventDefault();
                                    startRecording('keyToolbarBoundingBox');
                                }}
                            >
                                {#if recordingShortcut === 'keyToolbarBoundingBox'}
                                    <span class="italic opacity-70">Press a key...</span>
                                {:else}
                                    <span>{shortcutSettings.keyToolbarBoundingBox}</span>
                                {/if}
                            </button>
                        </div>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="toggle-edit-mode" class="text-right text-foreground">
                                Toolbar instance segmentation
                            </Label>
                            <button
                                id="toggle-edit-mode"
                                type="button"
                                class="rounded-md border border-input bg-background p-2 text-left text-foreground"
                                onclick={(e) => {
                                    e.preventDefault();
                                    startRecording('keyToolbarSegmentationMask');
                                }}
                            >
                                {#if recordingShortcut === 'keyToolbarSegmentationMask'}
                                    <span class="italic opacity-70">Press a key...</span>
                                {:else}
                                    <span>{shortcutSettings.keyToolbarSegmentationMask}</span>
                                {/if}
                            </button>
                        </div>
                    </div>

                    <!-- Grid View Settings -->
                    <div class="space-y-4">
                        <h3 class="text-lg font-medium text-foreground">Display Settings</h3>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="grid-view-rendering" class="text-right text-foreground">
                                Grid View Rendering
                            </Label>
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
                        </div>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label for="show-sample-filenames" class="text-right text-foreground">
                                Show filenames in grid view
                            </Label>
                            <Switch
                                id="show-sample-filenames"
                                bind:checked={showSampleFilenames}
                                disabled={isSaving}
                            />
                        </div>
                    </div>

                    <!-- Annotation Text Labels Setting -->
                    <div class="space-y-4">
                        <h3 class="text-lg font-medium text-foreground">Annotation Settings</h3>
                        <div class="grid grid-cols-2 items-center gap-4">
                            <Label
                                for="show-annotation-text-labels"
                                class="text-right text-foreground"
                            >
                                Show Annotation Text Labels
                            </Label>
                            <Switch
                                id="show-annotation-text-labels"
                                bind:checked={showAnnotationTextLabels}
                                disabled={isSaving}
                            />
                        </div>
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
