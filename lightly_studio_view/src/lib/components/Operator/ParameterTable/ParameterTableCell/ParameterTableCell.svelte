<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import type { OperatorParameterColumn } from '$lib/hooks';
    import { getCellConfig, type ParameterTableRow } from '../../parameterTypeConfig';

    interface Props {
        column: OperatorParameterColumn;
        value: ParameterTableRow[string] | undefined;
        isInvalid: boolean;
        label: string;
        testId: string;
        onUpdate: (value: ParameterTableRow[string]) => void;
    }

    let { column, value, isInvalid, label, testId, onUpdate }: Props = $props();

    const config = $derived(getCellConfig(column));
</script>

{#if config.type === 'bool'}
    <!-- A checkbox always has a value, so a boolean cell is never flagged as missing: doing so
         would turn "required" into "must be checked". -->
    <Checkbox
        checked={value === true}
        aria-label={label}
        onCheckedChange={(checked: boolean | 'indeterminate') => onUpdate(checked === true)}
        data-testid={testId}
    />
{:else}
    <Input
        type={config.inputType}
        step={config.step}
        value={value ?? ''}
        aria-label={label}
        aria-invalid={isInvalid}
        oninput={(event: Event) =>
            onUpdate(config.parse((event.currentTarget as HTMLInputElement).value))}
        data-testid={testId}
    />
{/if}
