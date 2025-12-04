<script lang="ts">
    import { onMount } from 'svelte';
    import { getOperators, type RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import AlertCircle from '@lucide/svelte/icons/alert-circle';
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useOperatorsDialog } from '$lib/hooks/useOperatorsDialog/useOperatorsDialog';
    import OperatorDialog from '$lib/components/Operator/OperatorDialog.svelte';

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
                    {operators.length}
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
                        {#each operators as operator}
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
