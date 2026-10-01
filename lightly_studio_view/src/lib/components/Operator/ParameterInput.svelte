<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import type { ParameterValue } from './parameterTypeConfig';

    interface Props {
        name: string;
        value: ParameterValue;
        required: boolean;
        isMissing: boolean;
        description?: string;
        inputType?: 'text' | 'number';
        step?: string;
        parse?: (value: string) => string | number;
        onUpdate: (value: ParameterValue) => void;
    }

    let {
        name,
        value,
        required,
        isMissing,
        description,
        inputType = 'text',
        step,
        parse,
        onUpdate
    }: Props = $props();
</script>

<div class="space-y-2">
    <Label for={name}>
        {name}
        {#if required}
            <span class="text-destructive-text">*</span>
        {/if}
    </Label>

    <Input
        id={name}
        type={inputType}
        {step}
        value={value ?? ''}
        aria-invalid={isMissing}
        oninput={(e: Event) => {
            const val = (e.currentTarget as HTMLInputElement).value;
            const parser = parse ?? ((v) => v);
            onUpdate(parser(val));
        }}
        placeholder={description || `Enter ${name}`}
    />

    {#if description}
        <p class="text-sm text-muted-foreground">
            {description}
        </p>
    {/if}
    <!-- An optional field only blocks once the user typed something unusable — whitespace, or a number
         input still reading '' mid-edit — so asking for a value would be wrong there. -->
    {#if isMissing}
        <p class="text-sm text-destructive-text">
            {required ? 'This field is required.' : 'Enter a valid value or clear this field.'}
        </p>
    {/if}
</div>
