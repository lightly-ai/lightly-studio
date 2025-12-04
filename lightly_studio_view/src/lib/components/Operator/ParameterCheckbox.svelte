<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Label } from '$lib/components/ui/label';
    import type { ParameterValue } from './parameterTypeConfig';

    interface Props {
        name: string;
        value: ParameterValue;
        required: boolean;
        isMissing: boolean;
        description?: string;
        onUpdate: (value: ParameterValue) => void;
    }

    let { name, value, required, isMissing, description, onUpdate }: Props = $props();
</script>

<div class="space-y-2">
    <div class="flex items-center space-x-2">
        <Checkbox
            id={name}
            checked={Boolean(value)}
            aria-invalid={required && isMissing}
            onCheckedChange={(checked: boolean | 'indeterminate') => onUpdate(checked === true)}
        />
        <Label for={name}>
            {name}
            {#if required}
                <span class="text-destructive">*</span>
            {/if}
        </Label>
    </div>
    {#if description}
        <p class="pl-6 text-sm text-muted-foreground">
            {description}
        </p>
    {/if}
    {#if required && isMissing}
        <p class="pl-6 text-sm text-destructive">This field is required.</p>
    {/if}
</div>
