<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import {
        executeOperator,
        getOperatorParameters,
        type RegisteredOperatorMetadata
    } from '$lib/api/lightly_studio_local';
    import { toast } from 'svelte-sonner';
    import type { Operator } from '$lib/hooks/useOperators/useOperators';
    import { createOperatorFromMetadata } from '$lib/hooks/useOperators/useOperators';
    import {
        type ParameterValue,
        type ParameterValues,
        isValueFilled,
        buildInitialParameters,
        getParameterConfig
    } from './parameterTypeConfig';

    interface Props {
        operatorMetadata: RegisteredOperatorMetadata;
        datasetId?: string;
        isOpen: boolean;
        onOpenChange: (open: boolean) => void;
    }

    let { operatorMetadata, datasetId, isOpen, onOpenChange }: Props = $props();
    let operator: Operator | null = $state(null);
    let isLoadingParameters = $state(false);
    let loadError = $state<string | null>(null);
    let parameters = $state<ParameterValues>({});
    let isExecuting = $state(false);
    let executionError = $state<string | undefined>(undefined);
    let executionSuccess = $state<string | undefined>(undefined);

    function resetExecutionState() {
        executionError = undefined;
        executionSuccess = undefined;
        isExecuting = false;
    }

    async function loadOperatorDefinition(metadata: RegisteredOperatorMetadata) {
        isLoadingParameters = true;
        loadError = null;
        //TODO (Jonas 12/2025): This might lead to a raise condition, but very unlikely.
        try {
            const response = await getOperatorParameters({
                path: { operator_id: metadata.operator_id }
            });
            if (response.error) {
                throw new Error(String(response.error) || 'Failed to load parameters');
            }

            operator = createOperatorFromMetadata(metadata, response.data ?? []);
            parameters = buildInitialParameters(operator);
            resetExecutionState();
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            loadError = message;
            operator = null;
            parameters = {};
            toast.error('Unable to load operator parameters', { description: message });
        } finally {
            isLoadingParameters = false;
        }
    }

    // Load operator definition and initialize parameters when metadata changes
    $effect(() => {
        loadOperatorDefinition(operatorMetadata);
    });

    let previousIsOpen = isOpen;
    $effect(() => {
        if (!isOpen && previousIsOpen) {
            parameters = operator ? buildInitialParameters(operator) : {};
            resetExecutionState();
        }
        previousIsOpen = isOpen;
    });

    async function handleExecute() {
        if (!operator || !datasetId || !isFormValid) {
            executionError = !datasetId
                ? 'Dataset not available. Please open a dataset first.'
                : 'Please fill in all required parameters.';
            return;
        }

        isExecuting = true;
        executionError = undefined;
        executionSuccess = undefined;

        try {
            const response = await executeOperator({
                path: { dataset_id: datasetId, operator_id: operator.id },
                body: { parameters }
            });

            if (response.error) {
                throw new Error(String(response.error) || 'Execution failed');
            }
            if (!response.data) throw new Error('Operator execution returned no result.');

            if (response.data.success) {
                executionSuccess = response.data.message || 'Execution succeeded.';
                toast.success('Operator executed', { description: executionSuccess });
            } else {
                executionError = response.data.message || 'Execution failed.';
                toast.error('Operator execution failed', { description: executionError });
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            executionError = message;
            toast.error('Operator execution failed', { description: message });
        } finally {
            isExecuting = false;
        }
    }

    const isFormValid = $derived.by(() => {
        if (!operator) return false;
        return operator.parameters.every((param) => {
            if (!(param.required ?? true)) return true;
            return isValueFilled(parameters[param.name], param.type);
        });
    });

    function updateParameter(paramName: string, value: ParameterValue) {
        parameters = { ...parameters, [paramName]: value };
    }
</script>

<Dialog.Root open={isOpen} {onOpenChange}>
    <Dialog.Content class="max-h-[85vh] overflow-y-auto sm:max-w-md">
        <Dialog.Header>
            <Dialog.Title>
                {operator?.name || operatorMetadata?.name || 'Operator'}
            </Dialog.Title>
            <Dialog.Description>
                Configure the parameters for this operator and click Execute to run it.
            </Dialog.Description>
        </Dialog.Header>

        {#if isLoadingParameters}
            <div
                class="flex items-center gap-2 rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground"
            >
                <Loader2 class="size-4 animate-spin" />
                <span>Loading operator parameters…</span>
            </div>
        {:else if loadError}
            <div
                class="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
            >
                {loadError}
            </div>
        {:else if operator && operator.parameters}
            <div class="space-y-4">
                {#each operator.parameters as param}
                    {@const config = getParameterConfig(param.type)}
                    {@const required = param.required ?? true}
                    {@const isMissing =
                        required && !isValueFilled(parameters[param.name], param.type)}

                    <config.component
                        name={param.name}
                        value={parameters[param.name] ?? ''}
                        {required}
                        {isMissing}
                        description={param.description}
                        onUpdate={(value) => updateParameter(param.name, value)}
                        {...config.props}
                    />
                {/each}

                {#if operator.parameters.length === 0}
                    <p class="text-sm text-muted-foreground">
                        This operator does not require any parameters. Click Execute to run it.
                    </p>
                {/if}

                {#if executionError}
                    <div class="text-sm text-destructive">Error: {executionError}</div>
                {/if}
                {#if executionSuccess}
                    <div class="text-sm text-emerald-600">{executionSuccess}</div>
                {/if}
            </div>

            <Dialog.Footer class="flex justify-end space-x-2">
                <Button variant="outline" onclick={() => onOpenChange(false)}>
                    {executionSuccess ? 'Close' : 'Cancel'}
                </Button>
                {#if !executionSuccess}
                    <Button onclick={handleExecute} disabled={!isFormValid || isExecuting}>
                        {isExecuting ? 'Executing...' : 'Execute'}
                    </Button>
                {/if}
            </Dialog.Footer>
        {:else}
            <div class="p-4">
                <p class="text-muted-foreground">
                    No operator selected or operator has no parameters.
                </p>
            </div>
        {/if}
    </Dialog.Content>
</Dialog.Root>
