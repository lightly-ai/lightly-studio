<script lang="ts">
    import { onMount } from 'svelte';
    import type { components } from '$lib/schema';
    import client from '$lib/services/dataset';
    import { Button } from '$lib/components/ui';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import AlertCircle from '@lucide/svelte/icons/alert-circle';
    import { Popover, PopoverContent, PopoverTrigger } from '$lib/components/ui/popover';
    import NetworkIcon from '@lucide/svelte/icons/network';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import {
        Dialog,
        DialogContent,
        DialogDescription,
        DialogHeader,
        DialogTitle
    } from '$lib/components/ui/dialog';
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

{#if operators.length > 0}
    <Popover bind:open={$isDropdownOpen}>
        <PopoverTrigger>
            <Button
                variant="ghost"
                class="nav-button flex items-center space-x-2 {$isDropdownOpen}"
                title={'Operators'}
            >
                <NetworkIcon class="size-4" />
                <span>Operators</span>
                <ChevronDown class="size-4" />
            </Button>
        </PopoverTrigger>
        <PopoverContent class="w-[480px] p-0">
            <div
                class="max-h-[calc(10*2.5rem)] overflow-y-auto"
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
        </PopoverContent>
    </Popover>

    <Dialog bind:open={isOperatorDialogOpen}>
        <DialogContent class="sm:max-w-[425px]">
            <DialogHeader>
                <DialogTitle>{activeOperator?.name ?? 'Operator details'}</DialogTitle>
                <DialogDescription>
                    This placeholder dialog confirms the operator selection. The detailed menu will
                    be added later.
                </DialogDescription>
            </DialogHeader>
            {#if activeOperator}
                <p class="text-sm text-foreground">Operator ID: {activeOperator.operator_id}</p>
            {/if}
        </DialogContent>
    </Dialog>
{/if}
