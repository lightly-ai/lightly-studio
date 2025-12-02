<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { Checkbox } from '$lib/components/ui/checkbox';
    import Loader2 from '@lucide/svelte/icons/loader-2';
    import {
        executeOperator,
        getOperatorParameters,
        type RegisteredOperatorMetadata
    } from '$lib/api/lightly_studio_local';
    import { toast } from 'svelte-sonner';
    import type { Operator, OperatorParameter } from '$lib/hooks/useOperators/useOperators';
    import { createOperatorFromMetadata } from '$lib/hooks/useOperators/useOperators';

    interface Props {
        operatorMetadata: RegisteredOperatorMetadata | null;
        datasetId?: string;
        isOpen: boolean;
        onOpenChange: (open: boolean) => void;
    }

    let { operatorMetadata, datasetId, isOpen, onOpenChange }: Props = $props();
    let operator: Operator | null = $state(null);
    let isLoadingParameters = $state(false);
    let loadError = $state<string | null>(null);
    let parameters = $state<Record<string, any>>({});
    let isExecuting = $state(false);
    let executionError = $state<string | undefined>(undefined);
    let executionSuccess = $state<string | undefined>(undefined);
    let fetchToken = 0;

    type ParameterControl =
        | {
              kind: 'checkbox';
          }
        | {
              kind: 'input';
              inputType: 'text' | 'number';
              step?: string;
              parse?: (value: string) => string | number;
          };

    const parseIntegerValue = (value: string) => (value === '' ? '' : Number.parseInt(value, 10));
    const parseFloatValue = (value: string) => (value === '' ? '' : Number.parseFloat(value));
    const identity = (value: string) => value;

    const PARAMETER_CONTROLS: Record<OperatorParameter['type'] | 'default', ParameterControl> = {
        bool: { kind: 'checkbox' },
        int: { kind: 'input', inputType: 'number', parse: parseIntegerValue },
        float: { kind: 'input', inputType: 'number', step: '0.01', parse: parseFloatValue },
        string: { kind: 'input', inputType: 'text', parse: identity },
        default: { kind: 'input', inputType: 'text', parse: identity }
    };

    const getControlForParameter = (parameter: OperatorParameter): ParameterControl => {
        return PARAMETER_CONTROLS[parameter.type] ?? PARAMETER_CONTROLS.default;
    };

    const buildInitialParameters = (selectedOperator: Operator) => {
        const initial: Record<string, any> = {};
        for (const param of selectedOperator.parameters) {
            if (param.default !== undefined) {
                initial[param.name] = param.default;
            } else if (param.type === 'bool') {
                initial[param.name] = false;
            } else {
                initial[param.name] = '';
            }
        }
        return initial;
    };

    const resetExecutionState = () => {
        executionError = undefined;
        executionSuccess = undefined;
        isExecuting = false;
    };

    const formatErrorMessage = (error: unknown): string => {
        if (!error) return 'An unknown error occurred.';
        if (typeof error === 'string') return error;
        if (error instanceof Error) return error.message;

        if (Array.isArray(error)) {
            return (
                error
                    .map((item) => {
                        if (!item) return '';
                        if (typeof item === 'string') return item;
                        if (
                            typeof item === 'object' &&
                            'msg' in item &&
                            typeof item.msg === 'string'
                        ) {
                            return item.msg;
                        }
                        return JSON.stringify(item);
                    })
                    .filter(Boolean)
                    .join(', ') || 'An unknown error occurred.'
            );
        }

        if (typeof error === 'object' && 'detail' in (error as any)) {
            return formatErrorMessage((error as { detail: unknown }).detail);
        }

        try {
            return JSON.stringify(error);
        } catch {
            return 'An unknown error occurred.';
        }
    };

    const loadOperatorDefinition = async (metadata: RegisteredOperatorMetadata) => {
        const token = ++fetchToken;
        isLoadingParameters = true;
        loadError = null;
        try {
            const response = await getOperatorParameters({
                path: { operator_id: metadata.operator_id }
            });
            if (response.error) {
                throw new Error(formatErrorMessage(response.error));
            }
            if (token !== fetchToken) return;
            operator = createOperatorFromMetadata(metadata, response.data ?? []);
            parameters = buildInitialParameters(operator);
            resetExecutionState();
        } catch (error) {
            if (token !== fetchToken) return;
            const message = error instanceof Error ? error.message : formatErrorMessage(error);
            loadError = message;
            operator = {
                id: metadata.operator_id,
                name: metadata.name,
                parameters: []
            };
            parameters = {};
            toast.error('Unable to load operator parameters', { description: message });
        } finally {
            if (token === fetchToken) {
                isLoadingParameters = false;
            }
        }
    };

    // Initialize parameters only when operator actually changes
    $effect(() => {
        if (!operatorMetadata) {
            fetchToken += 1;
            operator = null;
            parameters = {};
            loadError = null;
            isLoadingParameters = false;
            resetExecutionState();
            return;
        }
        loadOperatorDefinition(operatorMetadata);
    });

    // Reset execution state when dialog closes so the next open starts fresh
    let previousIsOpen = isOpen;
    $effect(() => {
        if (!isOpen && previousIsOpen) {
            if (operator) parameters = buildInitialParameters(operator);
            else parameters = {};
            resetExecutionState();
        }
        previousIsOpen = isOpen;
    });

    const handleExecute = async () => {
        if (!operator) return;
        if (!datasetId) {
            executionError = 'Dataset not available. Please open a dataset first.';
            return;
        }
        try {
            isExecuting = true;
            executionError = undefined;
            executionSuccess = undefined;

            const response = await executeOperator({
                path: {
                    dataset_id: datasetId,
                    operator_id: operator.id
                },
                body: { parameters }
            });

            if (response.error) {
                throw new Error(formatErrorMessage(response.error));
            }
            if (!response.data) {
                throw new Error('Operator execution returned no result.');
            }

            if (response.data.success) {
                executionSuccess = response.data.message || 'Execution succeeded.';
                toast.success('Operator executed', { description: executionSuccess });
            } else {
                executionError = response.data.message || 'Execution failed.';
                toast.error('Operator execution failed', { description: executionError });
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : formatErrorMessage(error);
            executionError = message;
            toast.error('Operator execution failed', { description: message });
        } finally {
            isExecuting = false;
        }
    };

    const isFormValid = $derived(() => {
        if (!operator) return false;

        // Check if all required parameters have values
        return operator.parameters.every((param) => {
            if (!param.required) return true;
            const value = parameters[param.name] ?? param.default;

            // For boolean parameters, any value (true/false) is valid
            if (param.type === 'bool') return value !== undefined;

            // For other parameters, check for non-empty strings/values
            return value !== undefined && value !== '' && value !== null;
        });
    });

    function updateParameter(paramName: string, value: any) {
        parameters = { ...parameters, [paramName]: value };
    }
</script>

<Dialog.Root open={isOpen} {onOpenChange}>
    <Dialog.Content class="sm:max-w-md">
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
                    {@const control = getControlForParameter(param)}
                    <div class="space-y-2">
                        {#if control.kind === 'checkbox'}
                            <div class="space-y-2">
                                <div class="flex items-center space-x-2">
                                    <Checkbox
                                        id={param.name}
                                        checked={Boolean(
                                            parameters[param.name] ?? param.default ?? false
                                        )}
                                        onCheckedChange={(checked: boolean | 'indeterminate') =>
                                            updateParameter(param.name, checked === true)}
                                    />
                                    <Label for={param.name}>
                                        {param.name}
                                        {#if param.required}
                                            <span class="text-destructive">*</span>
                                        {/if}
                                    </Label>
                                </div>
                                {#if param.description}
                                    <p class="pl-6 text-sm text-muted-foreground">
                                        {param.description}
                                    </p>
                                {/if}
                            </div>
                        {:else if control.kind === 'input'}
                            <Label for={param.name}>
                                {param.name}
                                {#if param.required}
                                    <span class="text-destructive">*</span>
                                {/if}
                            </Label>

                            <Input
                                id={param.name}
                                type={control.inputType}
                                step={control.step}
                                value={parameters[param.name] ?? param.default ?? ''}
                                oninput={(e: Event) => {
                                    const value = (e.currentTarget as HTMLInputElement).value;
                                    const parser = control.parse ?? identity;
                                    updateParameter(param.name, parser(value));
                                }}
                                placeholder={param.description || `Enter ${param.name}`}
                            />

                            {#if param.description}
                                <p class="text-sm text-muted-foreground">
                                    {param.description}
                                </p>
                            {/if}
                        {/if}
                    </div>
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
