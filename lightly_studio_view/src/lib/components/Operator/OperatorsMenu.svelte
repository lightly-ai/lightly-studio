<script lang="ts">
    import { onMount } from 'svelte';
    import { getOperators, type RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components/ui';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import AlertCircle from '@lucide/svelte/icons/alert-circle';
    import NetworkIcon from '@lucide/svelte/icons/network';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import * as Dialog from '$lib/components/ui/dialog';

    let operators: RegisteredOperatorMetadata[] = $state([]);
    let selectedOperatorId: string | undefined = $state(undefined);
    let isLoading = $state(true);
    let errorMessage: string | null = $state(null);
    let isOperatorDialogOpen = $state(false);
    let activeOperator: RegisteredOperatorMetadata | null = $state(null);

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

    const handleOperatorClick = (operator: RegisteredOperatorMetadata) => {
        selectedOperatorId = operator.operator_id;
        activeOperator = operator;
        isOperatorDialogOpen = true;
    };
    let isDialogOpen = $state(false);
</script>

<Dialog.Root bind:open={isDialogOpen}>
    <Dialog.Trigger>
        <Button
            variant="ghost"
            class={`nav-button flex items-center space-x-2 ${
                isDialogOpen ? 'ring-ring ring-2' : ''
            }`}
            title={'Operators'}
        >
            <NetworkIcon class="size-4" />
            <span>Plugins</span>
            <ChevronDown class="size-4" />
        </Button>
    </Dialog.Trigger>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="border-border bg-background flex max-h-[80vh] w-[90vw] flex-col overflow-hidden p-0 sm:w-[520px]"
        >
            <div class="flex flex-wrap items-start justify-between gap-2 border-b px-4 py-3 pr-12">
                <div>
                    <h3 class="text-foreground text-base font-semibold">Plugins</h3>
                    <p class="text-muted-foreground text-sm">Select a plugin to launch.</p>
                </div>
                <span
                    class="bg-secondary text-secondary-foreground inline-flex items-center rounded-full px-2 py-1 text-xs font-medium"
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
                    <div class="text-muted-foreground flex items-center gap-2 p-4 text-sm">
                        <Loader2 class="size-4 animate-spin" />
                        <span>Loading plugins…</span>
                    </div>
                {:else if errorMessage}
                    <div class="text-destructive flex items-center gap-2 p-4 text-sm">
                        <AlertCircle class="size-4" />
                        <span>{errorMessage}</span>
                    </div>
                {:else if operators.length === 0}
                    <div class="text-muted-foreground p-4 text-sm">No plugins available.</div>
                {:else}
                    <ul class="divide-border divide-y">
                        {#each operators as operator}
                            <li>
                                <button
                                    type="button"
                                    class={`hover:bg-muted focus-visible:ring-ring flex w-full items-center justify-between gap-2 p-3 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 ${
                                        selectedOperatorId === operator.operator_id
                                            ? 'bg-muted'
                                            : ''
                                    }`}
                                    onclick={() => handleOperatorClick(operator)}
                                >
                                    <span class="text-foreground font-medium">{operator.name}</span>
                                    <ChevronRight class="text-muted-foreground size-4" />
                                </button>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>

<Dialog.Root open={isOperatorDialogOpen} onOpenChange={(open) => (isOperatorDialogOpen = open)}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[425px]">
            <Dialog.Header>
                <Dialog.Title>{activeOperator?.name ?? 'Operator details'}</Dialog.Title>
                <Dialog.Description>
                    This placeholder dialog confirms the plugin selection. The detailed menu will be
                    added later.
                </Dialog.Description>
            </Dialog.Header>
            {#if activeOperator}
                <p class="text-foreground text-sm">Operator ID: {activeOperator.operator_id}</p>
            {/if}
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
