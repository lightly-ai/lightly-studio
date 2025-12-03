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

    type ParameterValue = string | number | boolean | null;
    type ParameterValues = Record<string, ParameterValue>;

    let { operatorMetadata, datasetId, isOpen, onOpenChange }: Props = $props();
    let operator: Operator | null = $state(null);
    let isLoadingParameters = $state(false);
    let loadError = $state<string | null>(null);
    let parameters = $state<ParameterValues>({});
    let isExecuting = $state(false);
    let executionError = $state<string | undefined>(undefined);
    let executionSuccess = $state<string | undefined>(undefined);
    let fetchToken = 0;

    type ParameterControl =
        | {
              kind: 'checkbox';
              inputType: 'boolean';
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
        bool: { kind: 'checkbox', inputType: 'boolean' },
        int: { kind: 'input', inputType: 'number', parse: parseIntegerValue },
        float: { kind: 'input', inputType: 'number', step: '0.01', parse: parseFloatValue },
        string: { kind: 'input', inputType: 'text', parse: identity },
        default: { kind: 'input', inputType: 'text', parse: identity }
    };

    const getControlForParameter = (parameter: OperatorParameter): ParameterControl => {
        return PARAMETER_CONTROLS[parameter.type] ?? PARAMETER_CONTROLS.default;
    };

    const toParameterValue = (value: unknown, fallback: ParameterValue = ''): ParameterValue => {
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
            return value;
        }
        if (value === null) {
            return null;
        }
        return fallback;
    };

    const isParameterRequired = (param: OperatorParameter): boolean => {
        return param.required ?? true;
    };

    const buildInitialParameters = (selectedOperator: Operator) => {
        const initial: ParameterValues = {};
        for (const param of selectedOperator.parameters) {
            if (param.default !== undefined) {
                initial[param.name] = toParameterValue(
                    param.default,
                    param.type === 'bool' ? false : ''
                );
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

    type ErrorWithDetail = { detail: unknown };
    const hasDetail = (error: unknown): error is ErrorWithDetail => {
        return typeof error === 'object' && error !== null && 'detail' in error;
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

        if (hasDetail(error)) {
            return formatErrorMessage(error.detail);
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
        if (!isFormValid) {
            executionError = 'Please fill in all required parameters.';
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

    const isRequiredValueFilled = (value: ParameterValue, type: string): boolean => {
        if (value === undefined || value === null) {
            return false;
        }
        if (type === 'boolean') {
            return value === true;
        }
        if (type === 'text') {
            if (typeof value === 'string') {
                return value.trim().length > 0;
            }
            return false;
        }
        if (type === 'number') {
            if (typeof value === 'number') {
                return Number.isFinite(value);
            }
            return false;
        }
        return value !== '';
    };

    type MissingMap = Record<string, boolean>;
    const missingRequiredParameters: MissingMap = $derived.by(() => {
        if (!operator) return {} as MissingMap;

        const missing: MissingMap = {};
        for (const param of operator.parameters) {
            console.log('RequiredField', param.name, parameters[param.name], param.type);
            missing[param.name] = false;
            if (isParameterRequired(param)) {
                missing[param.name] = !isRequiredValueFilled(parameters[param.name], param.type);
            }
        }

        return missing;
    });

    const isFormValid = $derived.by(() => {
        if (!operator) return false;
        return Object.values(missingRequiredParameters).every((v) => v === false);
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
                class="border-border text-muted-foreground flex items-center gap-2 rounded-md border border-dashed p-4 text-sm"
            >
                <Loader2 class="size-4 animate-spin" />
                <span>Loading operator parameters…</span>
            </div>
        {:else if loadError}
            <div
                class="border-destructive/30 bg-destructive/10 text-destructive rounded-md border p-4 text-sm"
            >
                {loadError}
            </div>
        {:else if operator && operator.parameters}
            <div class="space-y-4">
                {#each operator.parameters as param}
                    {@const control = getControlForParameter(param)}
                    {@const required = isParameterRequired(param)}
                    <div class="space-y-2">
                        {#if control.kind === 'checkbox'}
                            <div class="space-y-2">
                                <div class="flex items-center space-x-2">
                                    <Checkbox
                                        id={param.name}
                                        checked={Boolean(parameters[param.name])}
                                        aria-invalid={required &&
                                            missingRequiredParameters[param.name]}
                                        onCheckedChange={(checked: boolean | 'indeterminate') =>
                                            updateParameter(param.name, checked === true)}
                                    />
                                    <Label for={param.name}>
                                        {param.name}
                                        {#if required}
                                            <span class="text-destructive">*</span>
                                        {/if}
                                    </Label>
                                </div>
                                {#if param.description}
                                    <p class="text-muted-foreground pl-6 text-sm">
                                        {param.description}
                                    </p>
                                {/if}
                                {#if required && missingRequiredParameters[param.name]}
                                    <p class="text-destructive pl-6 text-sm">
                                        This field is required.
                                    </p>
                                {/if}
                            </div>
                        {:else if control.kind === 'input'}
                            <Label for={param.name}>
                                {param.name}
                                {#if required}
                                    <span class="text-destructive">*</span>
                                {/if}
                            </Label>

                            <Input
                                id={param.name}
                                type={control.inputType}
                                step={control.step}
                                value={parameters[param.name] ?? ''}
                                aria-invalid={required && missingRequiredParameters[param.name]}
                                oninput={(e: Event) => {
                                    const value = (e.currentTarget as HTMLInputElement).value;
                                    const parser = control.parse ?? identity;
                                    updateParameter(param.name, parser(value));
                                }}
                                placeholder={param.description || `Enter ${param.name}`}
                            />

                            {#if param.description}
                                <p class="text-muted-foreground text-sm">
                                    {param.description}
                                </p>
                            {/if}
                            {#if required && missingRequiredParameters[param.name]}
                                <p class="text-destructive text-sm">This field is required.</p>
                            {/if}
                        {/if}
                    </div>
                {/each}

                {#if operator.parameters.length === 0}
                    <p class="text-muted-foreground text-sm">
                        This operator does not require any parameters. Click Execute to run it.
                    </p>
                {/if}

                {#if executionError}
                    <div class="text-destructive text-sm">Error: {executionError}</div>
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
