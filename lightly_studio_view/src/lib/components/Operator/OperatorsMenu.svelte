<script lang="ts">
    import { onMount } from 'svelte';
    import type { components } from '$lib/schema';
    import client from '$lib/services/dataset';
    import { Button } from '$lib/components/ui';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import AlertCircle from '@lucide/svelte/icons/alert-circle';
    import NetworkIcon from '@lucide/svelte/icons/network';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import * as Dialog from '$lib/components/ui/dialog';
    import { writable } from 'svelte/store';

    type RegisteredOperatorMetadata = components['schemas']['RegisteredOperatorMetadata'];

    let operators: RegisteredOperatorMetadata[] = [];
    let selectedOperatorId: string | undefined = undefined;
    let isLoading = true;
    let errorMessage: string | null = null;
    let isOperatorDialogOpen = false;
    let activeOperator: RegisteredOperatorMetadata | null = null;

    const loadOperators = async () => {
        isLoading = true;
        errorMessage = null;
        try {
            const response = await client.GET('/api/operators');
            if (response.error) {
                throw response.error;
            }
            operators = response.data ?? [];
        } catch (error) {
            errorMessage =
                error instanceof Error ? error.message : 'Failed to load operators. Please retry.';
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
    const isDropdownOpen = writable<boolean>(false);
</script>

<Dialog.Root open={$isDropdownOpen} onOpenChange={(open) => isDropdownOpen.set(open)}>
    <Dialog.Trigger>
        <Button
            variant="ghost"
            class={`nav-button flex items-center space-x-2 ${
                $isDropdownOpen ? 'ring-2 ring-ring' : ''
            }`}
            title={'Operators'}
        >
            <NetworkIcon class="size-4" />
            <span>Operators</span>
            <ChevronDown class="size-4" />
        </Button>
    </Dialog.Trigger>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content
            class="flex max-h-[80vh] w-[90vw] flex-col overflow-hidden border-border bg-background p-0 sm:w-[520px]"
        >
            <div class="flex flex-wrap items-start justify-between gap-2 border-b px-4 py-3 pr-12">
                <div>
                    <h3 class="text-base font-semibold text-foreground">Operators</h3>
                    <p class="text-sm text-muted-foreground">Select an operator to manage.</p>
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
                        <span>Loading operators…</span>
                    </div>
                {:else if errorMessage}
                    <div class="flex items-center gap-2 p-4 text-sm text-destructive">
                        <AlertCircle class="size-4" />
                        <span>{errorMessage}</span>
                    </div>
                {:else if operators.length === 0}
                    <div class="p-4 text-sm text-muted-foreground">No operators available.</div>
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
                                    on:click={() => handleOperatorClick(operator)}
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

<Dialog.Root open={isOperatorDialogOpen} onOpenChange={(open) => (isOperatorDialogOpen = open)}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[425px]">
            <Dialog.Header>
                <Dialog.Title>{activeOperator?.name ?? 'Operator details'}</Dialog.Title>
                <Dialog.Description>
                    This placeholder dialog confirms the operator selection. The detailed menu will
                    be added later.
                </Dialog.Description>
            </Dialog.Header>
            {#if activeOperator}
                <p class="text-sm text-foreground">Operator ID: {activeOperator.operator_id}</p>
            {/if}
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
