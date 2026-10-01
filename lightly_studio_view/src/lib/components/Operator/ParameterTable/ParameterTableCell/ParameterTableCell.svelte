<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Input } from '$lib/components/ui/input';
    import type { OperatorParameterColumn } from '$lib/hooks';
    import { getCellConfig, type ParameterTableRow } from '../../parameterTypeConfig';

    interface Props {
        /** The column the cell belongs to; its type decides how the cell is rendered and parsed. */
        column: OperatorParameterColumn;
        /** Current cell value, `undefined` while the row has no entry for this column yet. */
        value: ParameterTableRow[string] | undefined;
        /** Whether to mark the cell as invalid for assistive technology. */
        isInvalid: boolean;
        /** Accessible name of the cell. Column names repeat across rows, so it also carries the row. */
        label: string;
        /** `data-testid` of the rendered control. */
        testId: string;
        /** Called with the parsed value on every edit. */
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
