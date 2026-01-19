<script lang="ts">
    import { page } from '$app/state';
    import { writable, derived, get } from 'svelte/store';
    import type { ClassifierExportType } from '$lib/services/types';
    import { Button } from '$lib/components/ui';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { Checkbox, Alert } from '$lib/components';
    import * as Select from '$lib/components/ui/select';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Tabs, TabsContent, TabsList, TabsTrigger } from '$lib/components/ui/tabs';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
    import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import { useClassifiersMenu } from '$lib/hooks/useClassifiers/useClassifiersMenu';
    import { useQueryClient } from '@tanstack/svelte-query';
    import {
        readAnnotationLabelsOptions,
        countAnnotationsByCollectionOptions
    } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { Network as NetworkIcon } from '@lucide/svelte';
    import { Pencil } from '@lucide/svelte';
    import { Download } from '@lucide/svelte';
    import { Upload } from '@lucide/svelte';
    import { Play } from '@lucide/svelte';
    import { LoaderCircle as Loader2 } from '@lucide/svelte';
    import { Info } from '@lucide/svelte';

    const exportOptions: ClassifierExportType[] = ['sklearn', 'lightly'];

    // Subscribe to page params
    const collectionId = page.params.collection_id;

    const client = useQueryClient();

    const { isCreateClassifiersPanelOpen } = useCreateClassifiersPanel();
    const { isRefineClassifiersPanelOpen } = useRefineClassifiersPanel();
    const {
        isDialogOpen,
        activeTab,
        switchToManageTab,
        openClassifiersMenu,
        closeClassifiersMenu,
        scrollToClassifierId
    } = useClassifiersMenu();

    // Classifier hook
    const {
        error,
        classifiers,
        classifiersSelected,
        isLoading,
        classifierSelectionToggle,
        apply,
        saveClassifier,
        loadClassifier,
        startRefinement,
        startCreateClassifier,
        clearClassifiersSelected
    } = useClassifiers();
    const { getSelectedSampleIds } = useGlobalStorage();
    const selectedSampleIds = getSelectedSampleIds(collectionId);

    // Store-based state
    const exportType = writable<ClassifierExportType>('sklearn');
    const showExportDialog = writable(false);
    const selectedClassifierId = writable<string | null>(null);
    let shouldRestoreMenu = $state(false);

    // Derived stores
    const isApplyButtonEnabled = derived(
        [classifiersSelected, classifiers],
        ([$sel, $list]) => $sel.size > 0 && $list.length > 0
    );

    const triggerContent = derived(exportType, ($type) => $type || 'Select export type');

    // Sort classifiers alphabetically by name
    const sortedClassifiers = derived(classifiers, ($classifiers) => {
        return [...$classifiers].sort((a, b) => a.classifier_name.localeCompare(b.classifier_name));
    });

    // Handlers
    function handleDownload(classifierId: string) {
        selectedClassifierId.set(classifierId);
        showExportDialog.set(true);
    }

    function handleExportWithType() {
        const id = get(selectedClassifierId);
        const type = get(exportType);
        if (id) {
            saveClassifier(id, type);
            showExportDialog.set(false);
            selectedClassifierId.set(null);
        }
    }

    // Function to refresh LabelsMenu by invalidating annotation labels and counts queries
    function refreshLabelsMenu() {
        client.invalidateQueries({ queryKey: readAnnotationLabelsOptions().queryKey });
        client.invalidateQueries({
            queryKey: countAnnotationsByCollectionOptions({
                path: { collection_id: collectionId }
            }).queryKey
        });
    }

    async function runClassifier() {
        await apply();
        refreshLabelsMenu();
    }

    function handleNewClassifier() {
        shouldRestoreMenu = true;
        // TODO (Jonas 12/2025: use the passed in event instead)
        startCreateClassifier(new Event('click'));
        closeClassifiersMenu();
    }

    function handleLoadClassifier(event: Event) {
        loadClassifier(event);
        // Switch to manage tab after successful load
        switchToManageTab();
    }

    // Temporarily hide menu while wizard dialogs are open and restore afterwards
    $effect(() => {
        const wizardOpen = $isCreateClassifiersPanelOpen || $isRefineClassifiersPanelOpen;
        if (wizardOpen) {
            closeClassifiersMenu();
        } else if (shouldRestoreMenu) {
            openClassifiersMenu();
            shouldRestoreMenu = false;
        }
    });

    // Handle scrolling to and selecting a classifier
    $effect(() => {
        const classifierId = $scrollToClassifierId;
        if (classifierId) {
            // Use a small delay to ensure the DOM is updated
            setTimeout(() => {
                const element = document.querySelector(`[data-classifier-id="${classifierId}"]`);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // Select the classifier
                    classifierSelectionToggle(classifierId);
                }
            }, 50);
        }
    });

    // Clear selection when dropdown is closed
    $effect(() => {
        if (!$isDialogOpen) {
            clearClassifiersSelected();
        }
    });
</script>

<Dialog.Root
    open={$isDialogOpen}
    onOpenChange={(open) => (open ? openClassifiersMenu() : closeClassifiersMenu())}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="flex max-h-[85vh] w-[90vw] flex-col overflow-hidden border-border bg-background sm:w-[560px]"
        >
            <Dialog.Header>
                <Dialog.Title class="text-foreground">Classifier</Dialog.Title>
                <Dialog.Description class="text-muted-foreground">
                    Train and run Few Shot Classifiers using the embeddings.
                </Dialog.Description>
            </Dialog.Header>
            <div class="flex-1 overflow-y-auto">
                <div class="p-4 pb-0">
                    <div class="flex items-center justify-between">
                        <span
                            class="inline-flex items-center rounded-full bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground"
                        >
                            {$classifiers.length} total
                        </span>
                    </div>
                </div>

                <Tabs bind:value={$activeTab} class="mt-2 w-full">
                    <TabsList class="mx-4 mb-4 grid w-auto grid-cols-2 gap-0">
                        <TabsTrigger
                            value="create"
                            class="flex items-center justify-center px-1 py-2 text-xs"
                        >
                            Create
                        </TabsTrigger>
                        <TabsTrigger
                            value="manage"
                            class="flex items-center justify-center px-1 py-2 text-xs"
                        >
                            Manage & Run
                        </TabsTrigger>
                    </TabsList>
                    <!-- TODO(Horatiu, 10/2025):Extract tabs to separate subcomponents. -->
                    <!-- Create Tab -->
                    <TabsContent value="create" class="space-y-4 px-4 pb-4">
                        <div class="space-y-4">
                            <!-- Create New Classifier -->
                            <div class="space-y-3">
                                {#if $selectedSampleIds.size === 0}
                                    <div class="flex items-center gap-2">
                                        <p class="flex items-center gap-2 text-sm text-orange-600">
                                            <Info class="size-4" />
                                            Select samples to create a classifier
                                        </p>
                                    </div>
                                {:else}
                                    <p class="flex items-center gap-2 text-sm text-green-600">
                                        <Info class="size-4" />
                                        {$selectedSampleIds.size} samples selected
                                    </p>
                                    <Button
                                        variant="default"
                                        class="w-full"
                                        onclick={handleNewClassifier}
                                    >
                                        <NetworkIcon class="mr-2 size-4" />
                                        Create New Classifier
                                    </Button>
                                {/if}
                            </div>

                            <!-- Separator -->
                            <div class="border-t border-border"></div>

                            <!-- Load Classifier -->
                            <div class="space-y-3">
                                <div class="flex items-center gap-2">
                                    <h4 class="text-sm font-medium">Load Existing Classifier</h4>
                                </div>
                                <div class="relative">
                                    <input
                                        title="Load Classifier"
                                        type="file"
                                        accept=".pkl"
                                        class="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                                        onchange={handleLoadClassifier}
                                    />
                                    <Button variant="outline" class="w-full">
                                        <Upload class="mr-2 size-4" />
                                        Load Classifier (.pkl)
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </TabsContent>

                    <!-- Manage & Run Tab -->
                    <TabsContent value="manage" class="space-y-4 px-4 pb-4">
                        {#if $sortedClassifiers.length > 0}
                            <!-- Classifiers List -->
                            <div
                                class="max-h-48 space-y-2 overflow-y-auto dark:[color-scheme:dark]"
                            >
                                {#each $sortedClassifiers as classifier (classifier.classifier_id)}
                                    <div
                                        class="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50"
                                        data-classifier-id={classifier.classifier_id}
                                    >
                                        <div class="flex min-w-0 flex-1 items-center gap-3">
                                            <Checkbox
                                                name={classifier.classifier_id}
                                                label=""
                                                isChecked={$classifiersSelected.has(
                                                    classifier.classifier_id
                                                )}
                                                onCheckedChange={() =>
                                                    classifierSelectionToggle(
                                                        classifier.classifier_id
                                                    )}
                                            />
                                            <div class="min-w-0 flex-1">
                                                <p class="truncate text-sm font-medium">
                                                    {classifier.classifier_name}
                                                </p>
                                            </div>
                                        </div>
                                        <div class="flex items-center gap-1">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                title="Edit classifier"
                                                onclick={() => {
                                                    shouldRestoreMenu = true;
                                                    startRefinement(
                                                        'existing',
                                                        classifier.classifier_id,
                                                        classifier.classifier_name,
                                                        classifier.class_list,
                                                        collectionId
                                                    );
                                                    closeClassifiersMenu();
                                                }}
                                            >
                                                <Pencil class="size-4" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                title="Download classifier"
                                                onclick={() =>
                                                    handleDownload(classifier.classifier_id)}
                                            >
                                                <Download class="size-4" />
                                            </Button>
                                        </div>
                                    </div>
                                {/each}
                            </div>

                            <!-- Run Section -->
                            <div class="mt-4 border-t pt-4">
                                <div class="mb-3 flex items-center gap-2">
                                    <h4 class="text-sm font-medium">Run Classifiers</h4>
                                    <span
                                        class="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium {$classifiersSelected.size >
                                        0
                                            ? 'bg-primary text-primary-foreground'
                                            : 'bg-secondary text-secondary-foreground'}"
                                    >
                                        {$classifiersSelected.size} selected
                                    </span>
                                </div>

                                {#if $classifiersSelected.size > 0}
                                    <div class="rounded-lg bg-muted/50 p-4">
                                        <div class="flex items-start gap-2">
                                            <h4 class="mb-3 text-sm text-muted-foreground">
                                                Selected classifiers will be applied to your
                                                collection
                                            </h4>
                                            <Tooltip
                                                content="The results will be added as new annotations to the collection. New labels with the format 'classifier_class_name' will be created for each class of the classifier after a successful run."
                                            >
                                                <Info class="mt-0.5 size-4 text-muted-foreground" />
                                            </Tooltip>
                                        </div>
                                        <Button
                                            variant="default"
                                            class="w-full"
                                            disabled={!$isApplyButtonEnabled}
                                            onclick={runClassifier}
                                        >
                                            {#if $isLoading}
                                                <Loader2 class="mr-2 size-4 animate-spin" />
                                                Running Classifiers...
                                            {:else}
                                                <Play class="mr-2 size-4" />
                                                Run Selected Classifiers
                                            {/if}
                                        </Button>
                                    </div>
                                {:else}
                                    <div class="rounded-lg bg-muted/30 py-4 text-center">
                                        <Play class="mx-auto mb-2 size-8 text-muted-foreground" />
                                        <p class="text-sm text-muted-foreground">
                                            No classifiers selected
                                        </p>
                                    </div>
                                {/if}
                            </div>
                        {:else}
                            <div class="py-8 text-center">
                                <NetworkIcon class="mx-auto mb-3 size-12 text-muted-foreground" />
                                <p class="text-sm text-muted-foreground">No classifiers found</p>
                                <p class="mt-1 text-xs text-muted-foreground">
                                    Create your first classifier to get started
                                </p>
                            </div>
                        {/if}
                    </TabsContent>
                </Tabs>

                {#if $error}
                    <div class="border-t p-4">
                        <Alert title="Error occurred">{$error}</Alert>
                    </div>
                {/if}
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>

<Dialog.Root bind:open={$showExportDialog}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[420px]">
            <Dialog.Header>
                <Dialog.Title>Export Classifier</Dialog.Title>
            </Dialog.Header>
            <div class="grid gap-4 py-4">
                <div class="space-y-2">
                    <label for="exportType" class="text-sm font-medium"
                        >Select the export type for the classifier.</label
                    >
                    <Select.Root type="single" name="exportType" bind:value={$exportType}>
                        <Select.Trigger class="w-full">
                            {$triggerContent}
                        </Select.Trigger>
                        <Select.Content>
                            <Select.Group>
                                <Select.GroupHeading>Export Types</Select.GroupHeading>
                                {#each exportOptions as value (value)}
                                    <Select.Item {value} label={value}>
                                        {value}
                                    </Select.Item>
                                {/each}
                            </Select.Group>
                        </Select.Content>
                    </Select.Root>
                </div>

                <Button class="flex-1" onclick={() => handleExportWithType()}>Export</Button>
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
