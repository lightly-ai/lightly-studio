<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Label } from '$lib/components/ui/label';
    import { Select, SelectContent, SelectItem, SelectTrigger } from '$lib/components/ui/select';
    import { Switch } from '$lib/components/ui/switch';
    import { useSettings } from '$lib/hooks/useSettings';
    import { Settings as SettingsIcon } from '@lucide/svelte';

    // Get settings from the store
    const { settingsStore, isLoadedStore, saveSettings } = useSettings();

    let isOpen = $state(false);
    let isSaving = $state(false);

    // Initialize with default values first
    let shortcutSettings = $state({
        hideAnnotations: 'v',
        goBack: 'Escape'
    });
    let gridViewRendering = $state('contain');
    let showAnnotationTextLabels = $state<boolean>(true);
    let showSampleFilenames = $state<boolean>(false);

    let initialized = false;

    // Update local state when store changes
    $effect(() => {
        if ($settingsStore && $isLoadedStore && !initialized) {
            shortcutSettings = {
                hideAnnotations: $settingsStore.key_hide_annotations || 'v',
                goBack: $settingsStore.key_go_back || 'Escape'
            };
            gridViewRendering = $settingsStore.grid_view_sample_rendering || 'contain';
            showAnnotationTextLabels = Boolean($settingsStore.show_annotation_text_labels ?? true);
            showSampleFilenames = Boolean($settingsStore.show_sample_filenames ?? false);
            initialized = true;
        }
    });

    let recordingShortcut = $state(null);

    function setOpen(value) {
        isOpen = value;
        if (!value) {
            recordingShortcut = null;
        }
    }

    function handleGridViewRenderingChange(value) {
        gridViewRendering = value;
    }

    // Submit handler
    function handleFormSubmit(event) {
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
                grid_view_sample_rendering: gridViewRendering,
                show_annotation_text_labels: showAnnotationTextLabels,
                show_sample_filenames: showSampleFilenames
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
        if (recordingShortcut === 'hideAnnotations') {
            shortcutSettings.hideAnnotations = keyName;
        } else if (recordingShortcut === 'goBack') {
            shortcutSettings.goBack = keyName;
        }

        // Stop recording
        recordingShortcut = null;
    };
</script>

<svelte:window onkeydown={handleKeyDown} />

<Dialog.Root bind:open={isOpen}>
    <Dialog.Trigger>
        <Button variant="outline" class="gap-2">
            <SettingsIcon class="h-4 w-4" />
            <span>Settings</span>
        </Button>
    </Dialog.Trigger>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[500px]">
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
