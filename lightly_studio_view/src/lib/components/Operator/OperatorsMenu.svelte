<script lang="ts">
    import { onMount } from 'svelte';
    import type { components } from '$lib/schema';
    import client from '$lib/services/dataset';
    import { Select, SelectContent, SelectItem, SelectTrigger } from '$lib/components/ui/select';
    import { Button } from '$lib/components/ui';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import AlertCircle from '@lucide/svelte/icons/alert-circle';

    type RegisteredOperatorMetadata = components['schemas']['RegisteredOperatorMetadata'];

    let operators: RegisteredOperatorMetadata[] = [];
    let selectedOperatorId: string | undefined = undefined;
    let isLoading = true;
    let errorMessage: string | null = null;

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

    const handleValueChange = (value: string | string[] | undefined) => {
        if (typeof value === 'string') {
            selectedOperatorId = value;
        }
    };

    $: selectedOperatorName = operators.find(
        (operator) => operator.operator_id === selectedOperatorId
    )?.name;
</script>

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
        <div class="border-b">
            <Select
                type="single"
                disabled={isLoading || !!errorMessage || operators.length === 0}
                value={selectedOperatorId}
                onValueChange={handleValueChange}
            >
                <SelectTrigger>
                    <span class="flex items-center gap-2"> Operator </span>
                </SelectTrigger>
                <SelectContent>
                    {#each operators as operator}
                        <SelectItem value={operator.operator_id}>{operator.name}</SelectItem>
                    {/each}
                </SelectContent>
            </Select>
        </div>
    </PopoverContent>
</Popover>
