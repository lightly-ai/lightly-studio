<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import { SettingsDialogState } from './settingsDialogState.svelte';
    import { SettingsTabs } from './SettingsTabs';

    const { settingsStore, saveSettings } = useSettings();
    const { isSettingsDialogOpen, openSettingsDialog, closeSettingsDialog } = useSettingsDialog();

    const dialogState = new SettingsDialogState();
    let activeTab = $state('shortcuts');

    // Hydrate form state each time the dialog opens.
    let wasDialogOpen = false;
    $effect(() => {
        if ($isSettingsDialogOpen && !wasDialogOpen) {
            dialogState.hydrate($settingsStore);
            activeTab = 'shortcuts';
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
        dialogState.clearRecording();

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

<!--
    Keep keys from the app shortcuts on window. Let Escape through: Svelte skips
    the Bits UI document listener that closes the dialog after stopPropagation.
-->
<svelte:document
    onkeydown={(e) => {
        if (!$isSettingsDialogOpen) return;
        dialogState.handleKeyDown(e);
        if (e.key !== 'Escape') e.stopPropagation();
    }}
/>

<Dialog.Root open={$isSettingsDialogOpen} onOpenChange={(isOpen) => setOpen(isOpen)}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="flex h-[600px] max-h-[85vh] flex-col gap-0 border-border bg-background p-0 dark:[color-scheme:dark] sm:max-w-[760px]"
            onEscapeKeydown={(e) => {
                // Escape cancels shortcut recording instead of closing the dialog.
                if (!dialogState.recordingShortcut) return;
                e.preventDefault();
                dialogState.clearRecording();
            }}
        >
            <form onsubmit={handleFormSubmit} class="flex min-h-0 flex-1 flex-col">
                <Dialog.Header class="px-6 pt-6">
                    <Dialog.Title class="text-foreground">Settings</Dialog.Title>
                    <Dialog.Description class="sr-only">
                        Configure your application preferences.
                    </Dialog.Description>
                </Dialog.Header>

                <SettingsTabs bind:value={activeTab} {dialogState} />

                <Dialog.Footer
                    class="flex-row justify-end space-x-2 border-t border-border px-6 py-4"
                >
                    <Button
                        variant="outline"
                        buttonProps={{ type: 'button', onclick: () => setOpen(false) }}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="default"
                        buttonProps={{ type: 'submit' }}
                        isPending={dialogState.isSaving}
                        disabledReason={dialogState.hasChanges ? undefined : 'No changes to save'}
                    >
                        {dialogState.isSaving ? 'Saving...' : 'Save changes'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
