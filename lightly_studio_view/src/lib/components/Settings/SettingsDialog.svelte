<script lang="ts">
    import { Button } from '$lib/components';
    import * as Dialog from '$lib/components/ui/dialog';
    import * as Tabs from '$lib/components/ui/tabs';
    import { useSettings } from '$lib/hooks/useSettings';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import { SettingsDialogState } from './settingsDialogState.svelte';
    import { ShortcutsTab } from './ShortcutsTab';
    import { DisplayTab } from './DisplayTab';
    import { AnnotationsTab } from './AnnotationsTab';

    const { settingsStore, saveSettings } = useSettings();
    const { isSettingsDialogOpen, openSettingsDialog, closeSettingsDialog } = useSettingsDialog();

    const dialogState = new SettingsDialogState();
    const tabs = [
        { value: 'shortcuts', label: 'Shortcuts', component: ShortcutsTab },
        { value: 'display', label: 'Display', component: DisplayTab },
        { value: 'annotations', label: 'Annotations', component: AnnotationsTab }
    ];
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

    function handleTabChange(tab: string) {
        activeTab = tab;
        dialogState.clearRecording();
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
        >
            <form onsubmit={handleFormSubmit} class="flex min-h-0 flex-1 flex-col">
                <Dialog.Header class="px-6 pt-6">
                    <Dialog.Title class="text-foreground">Settings</Dialog.Title>
                    <Dialog.Description class="sr-only">
                        Configure your application preferences.
                    </Dialog.Description>
                </Dialog.Header>

                <Tabs.Root
                    value={activeTab}
                    onValueChange={handleTabChange}
                    class="flex min-h-0 flex-1 flex-col"
                >
                    <Tabs.List
                        class="mt-4 h-auto justify-start gap-6 rounded-none border-b border-border bg-transparent p-0 px-6"
                    >
                        {#each tabs as tab (tab.value)}
                            <Tabs.Trigger
                                value={tab.value}
                                class="-mb-px rounded-none border-b-2 border-transparent px-0 pb-2.5 pt-0 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none"
                            >
                                {tab.label}
                            </Tabs.Trigger>
                        {/each}
                    </Tabs.List>
                    {#each tabs as tab (tab.value)}
                        <Tabs.Content
                            value={tab.value}
                            class="mt-0 min-h-0 flex-1 overflow-y-auto px-6 py-4"
                        >
                            <tab.component {dialogState} />
                        </Tabs.Content>
                    {/each}
                </Tabs.Root>

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
                        buttonProps={{ type: 'submit', disabled: dialogState.isSaving }}
                    >
                        {dialogState.isSaving ? 'Saving...' : 'Save changes'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
