<script lang="ts">
    import { page } from '$app/stores';
    import { derived } from 'svelte/store';
    import { onMount } from 'svelte';
    import {
        getOperators,
        type RegisteredOperatorMetadata,
        OperatorScope
    } from '$lib/api/lightly_studio_local';
    import { useCollection } from '$lib/hooks/useCollection/useCollection';
    import { LoaderCircle as Loader2, AlertCircle, ChevronRight } from '@lucide/svelte';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useOperatorsDialog } from '$lib/hooks/useOperatorsDialog/useOperatorsDialog';
    import OperatorDialog from '$lib/components/Operator/OperatorDialog.svelte';
    import {
        useOperatorContext,
        type PageContext
    } from '$lib/hooks/useOperatorContext/useOperatorContext';

    let operators: RegisteredOperatorMetadata[] = $state([]);
    let selectedOperatorId: string | undefined = $state(undefined);
    let isLoading = $state(true);
    let errorMessage: string | null = $state(null);
    let isOperatorDialogOpen = $state(false);
    let activeOperatorMetadata: RegisteredOperatorMetadata | null = $state(null);

    const loadOperators = async () => {
        isLoading = true;
        errorMessage = null;
        try {
            const response = await getOperators();
            if (response.error) {
                throw response.error;
            }
            operators = response.data ?? [];
        } catch (error) {
            errorMessage =
                error instanceof Error ? error.message : 'Failed to load plugins. Please retry.';
            operators = [];
        } finally {
            isLoading = false;
        }
    };

    onMount(() => {
        loadOperators();
    });

    const { isOperatorsDialogOpen, openOperatorsDialog, closeOperatorsDialog } =
        useOperatorsDialog();

    const handleOperatorClick = (operator: RegisteredOperatorMetadata) => {
        selectedOperatorId = operator.operator_id;
        activeOperatorMetadata = operator;
        closeOperatorsDialog();
        isOperatorDialogOpen = true;
    };

    const pageContext = derived(page, ($p) => ({
        routeId: $p.route.id,
        collectionId: $p.params.collection_id ?? '',
        sampleId: $p.params.sampleId || $p.params.sample_id || null,
        annotationId: $p.params.annotationId || null
    }) satisfies PageContext);

    const { collectionId, currentScope } = useOperatorContext(pageContext);

    const { collection: collectionQuery } = $derived.by(() =>
        useCollection({ collectionId: $collectionId ?? '' })
    );

    const isRootCollection = $derived($collectionQuery.data?.parent_collection_id === null);

    const isApplicable = (operator: RegisteredOperatorMetadata): boolean => {
        if ($currentScope === null) return false;
        if (isRootCollection && operator.supported_scopes.includes(OperatorScope.ROOT)) return true;
        return operator.supported_scopes.includes($currentScope);
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
                    <p class="text-sm text-muted-foreground">Select a plugin to launch.</p>
                </div>
                <span
                    class="inline-flex items-center rounded-full bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground"
                >
                    {applicableOperators.length}
                </span>
            </div>
            <div
                class="max-h-[65vh] flex-1 overflow-y-auto"
                aria-live="polite"
                aria-busy={isLoading}
            >
                {#if isLoading}
                    <div class="flex items-center gap-2 p-4 text-sm text-muted-foreground">
                        <Loader2 class="size-4 animate-spin" />
                        <span>Loading plugins…</span>
                    </div>
                {:else if errorMessage}
                    <div class="flex items-center gap-2 p-4 text-sm text-destructive">
                        <AlertCircle class="size-4" />
                        <span>{errorMessage}</span>
                    </div>
                {:else if operators.length === 0}
                    <div class="p-4 text-sm text-muted-foreground">No plugins available.</div>
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
                                    <span class="font-medium text-foreground">{operator.name}</span>
                                    <ChevronRight class="size-4 text-muted-foreground" />
                                </button>
                            </li>
                        {/each}
                    </ul>

                    {#if inapplicableOperators.length > 0}
                        <div class="border-t border-border">
                            <p class="px-3 pb-1 pt-3 text-xs font-medium text-muted-foreground/60">
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
            </div>
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
