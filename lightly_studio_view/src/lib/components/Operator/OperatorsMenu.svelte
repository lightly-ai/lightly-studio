<script lang="ts">
    import { page } from '$app/stores';
    import { derived as storeDerived } from 'svelte/store';
    import {
        type RegisteredOperatorMetadata,
        type SampleType,
        OperatorScope
    } from '$lib/api/lightly_studio_local';
    import { LoaderCircle as Loader2, AlertCircle, ChevronRight, RefreshCw } from '@lucide/svelte';
    import * as Dialog from '$lib/components/ui/dialog';
    import * as Tabs from '$lib/components/ui/tabs';
    import { useOperatorsDialog } from '$lib/hooks/useOperatorsDialog/useOperatorsDialog';
    import { useOperatorsList } from '$lib/hooks';
    import OperatorDialog from '$lib/components/Operator/OperatorDialog.svelte';
    import PluginCatalog from '$lib/components/Operator/PluginCatalog/PluginCatalog.svelte';
    import {
        useOperatorContext,
        type PageContext
    } from '$lib/hooks/useOperatorContext/useOperatorContext';

    let selectedOperatorId: string | undefined = $state(undefined);
    let isOperatorDialogOpen = $state(false);
    let activeOperatorMetadata: RegisteredOperatorMetadata | null = $state(null);
    let activeTab: 'installed' | 'browse' = $state('installed');

    const { query: operatorsQuery, reloadMutation, reload } = useOperatorsList();
    const operators = $derived(operatorsQuery.data ?? []);
    const isLoading = $derived(operatorsQuery.isPending);
    const errorMessage = $derived(
        operatorsQuery.isError ? 'Failed to load plugins. Please retry.' : null
    );

    const { isOperatorsDialogOpen, openOperatorsDialog, closeOperatorsDialog } =
        useOperatorsDialog();

    // The menu stays mounted after the first open, so refresh the list on each open.
    $effect(() => {
        if ($isOperatorsDialogOpen) operatorsQuery.refetch();
    });

    const handleOperatorClick = (operator: RegisteredOperatorMetadata) => {
        selectedOperatorId = operator.operator_id;
        activeOperatorMetadata = operator;
        closeOperatorsDialog();
        isOperatorDialogOpen = true;
    };

    const pageContext = storeDerived(
        page,
        ($p) =>
            ({
                routeId: $p.route.id,
                collectionId: $p.params.collection_id ?? '',
                sampleId: $p.params.sampleId || $p.params.sample_id || null,
                annotationId: $p.params.annotationId || null,
                sampleType: ($p.params.collection_type as SampleType) ?? null
            }) satisfies PageContext
    );

    const { currentScope } = useOperatorContext(pageContext);

    const isDataset = $derived($page.data.collection?.parent_collection_id === null);

    const isApplicable = (operator: RegisteredOperatorMetadata): boolean => {
        if ($currentScope === null) return false;
        if (isDataset && operator.supported_scopes?.includes(OperatorScope.ROOT)) return true;
        return operator.supported_scopes?.includes($currentScope) ?? false;
    };

    const applicableOperators = $derived(operators.filter((op) => isApplicable(op)));
    const inapplicableOperators = $derived(operators.filter((op) => !isApplicable(op)));
</script>

<Dialog.Root
    open={$isOperatorsDialogOpen}
    onOpenChange={(open) => (open ? openOperatorsDialog() : closeOperatorsDialog())}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="flex max-h-[80vh] w-[90vw] flex-col overflow-hidden border-border bg-background p-0 sm:w-[520px]"
        >
            <div class="flex flex-wrap items-start justify-between gap-2 border-b px-4 py-3 pr-12">
                <div>
                    <h3 class="text-base font-semibold text-foreground">Plugins</h3>
                    <p class="text-sm text-muted-foreground">
                        Select a plugin to launch, or browse plugins to install.
                    </p>
                </div>
                <button
                    type="button"
                    class="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    title="Reload plugins installed from a terminal"
                    aria-label="Reload plugins"
                    disabled={reloadMutation.isPending}
                    onclick={reload}
                >
                    <RefreshCw class={`size-4 ${reloadMutation.isPending ? 'animate-spin' : ''}`} />
                </button>
            </div>
            <Tabs.Root bind:value={activeTab} class="flex min-h-0 flex-1 flex-col">
                <Tabs.List class="mx-4 mt-3 grid grid-cols-2">
                    <Tabs.Trigger value="installed">
                        Installed ({applicableOperators.length})
                    </Tabs.Trigger>
                    <Tabs.Trigger value="browse">Browse</Tabs.Trigger>
                </Tabs.List>
                <Tabs.Content
                    value="installed"
                    class="max-h-[60vh] flex-1 overflow-y-auto"
                    aria-live="polite"
                    aria-busy={isLoading}
                >
                    {#if isLoading}
                        <div class="flex items-center gap-2 p-4 text-sm text-muted-foreground">
                            <Loader2 class="size-4 animate-spin" />
                            <span>Loading plugins…</span>
                        </div>
                    {:else if errorMessage}
                        <div class="flex items-center gap-2 p-4 text-sm text-destructive-text">
                            <AlertCircle class="size-4" />
                            <span>{errorMessage}</span>
                        </div>
                    {:else if operators.length === 0}
                        <div class="p-4 text-sm text-muted-foreground">
                            <p>No plugins installed.</p>
                            <p class="mt-2">
                                Extend LightlyStudio with plugins to ingest/export data, run
                                model-assisted annotation, and automate workflows.
                                <button
                                    type="button"
                                    class="text-foreground underline underline-offset-4"
                                    onclick={() => (activeTab = 'browse')}
                                >
                                    Browse plugins
                                </button>
                                to install one, or build your own.
                            </p>
                        </div>
                    {:else}
                        <ul class="divide-y divide-border">
                            {#each applicableOperators as operator}
                                <li>
                                    <button
                                        type="button"
                                        class={`flex w-full items-center justify-between gap-2 p-3 text-left text-sm transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                                            selectedOperatorId === operator.operator_id
                                                ? 'bg-muted'
                                                : ''
                                        }`}
                                        onclick={() => handleOperatorClick(operator)}
                                    >
                                        <span class="font-medium text-foreground"
                                            >{operator.name}</span
                                        >
                                        <ChevronRight class="size-4 text-muted-foreground" />
                                    </button>
                                </li>
                            {/each}
                        </ul>

                        {#if inapplicableOperators.length > 0}
                            <div class="border-t border-border">
                                <p
                                    class="px-3 pb-1 pt-3 text-xs font-medium text-muted-foreground/60"
                                >
                                    Not applicable in current view
                                </p>
                                <ul class="divide-y divide-border">
                                    {#each inapplicableOperators as operator}
                                        <li>
                                            <div
                                                class="flex w-full cursor-not-allowed items-center justify-between gap-2 p-3 text-left text-sm opacity-40"
                                            >
                                                <span class="font-medium">{operator.name}</span>
                                                <ChevronRight class="size-4" />
                                            </div>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    {/if}
                </Tabs.Content>
                <Tabs.Content value="browse" class="max-h-[60vh] flex-1 overflow-y-auto">
                    <PluginCatalog isVisible={$isOperatorsDialogOpen && activeTab === 'browse'} />
                </Tabs.Content>
            </Tabs.Root>
            <Dialog.Footer class="px-4 pb-4">
                <a
                    href="https://docs.lightly.ai/studio/ecosystem/plugins/"
                    target="_blank"
                    rel="noreferrer"
                    class="mr-auto self-center text-xs text-muted-foreground underline-offset-4 hover:underline"
                >
                    Learn more about plugins →
                </a>
            </Dialog.Footer>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>

<OperatorDialog
    operatorMetadata={activeOperatorMetadata}
    isOpen={isOperatorDialogOpen}
    onOpenChange={(open) => {
        isOperatorDialogOpen = open;
        if (!open) {
            selectedOperatorId = undefined;
            activeOperatorMetadata = null;
        }
    }}
/>
