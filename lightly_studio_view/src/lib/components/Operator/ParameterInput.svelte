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
            <span class="text-destructive">*</span>
        {/if}
    </Label>

    <Input
        id={name}
        type={inputType}
        {step}
        value={value ?? ''}
        aria-invalid={required && isMissing}
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
    {#if required && isMissing}
        <p class="text-sm text-destructive">This field is required.</p>
    {/if}
</div>
