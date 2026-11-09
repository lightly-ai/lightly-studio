<script lang="ts">
    import { Input } from '$lib/components/ui/input';

    interface Props {
        label: string;
        bound: { min: number; max: number };
        value: { min: number; max: number };
        integer?: boolean;
        unit?: string;
        onValueCommit: (values: number[]) => void;
    }

    const { label, bound, value, integer = false, unit, onValueCommit }: Props = $props();
    const id = $props.id();
    let drafts = $state(['', '']);
    let dirty = $state([false, false]);
    let errors = $state(['', '']);
    let pending: number[] | undefined;

    const reset = () => {
        drafts = [String(value.min), String(value.max)];
        dirty = [false, false];
        errors = ['', ''];
    };
    $effect(() => {
        const acknowledged = pending?.[0] === value.min && pending?.[1] === value.max;
        pending = undefined;
        if (!acknowledged) reset();
    });

    const validate = (index: number): string => {
        const number = Number(drafts[index]);
        const min = index === 0 ? bound.min : value.min;
        const max = index === 0 ? value.max : bound.max;
        if (
            !drafts[index].trim() ||
            !Number.isFinite(number) ||
            (integer && !Number.isInteger(number))
        ) {
            return integer ? 'Enter a whole number.' : 'Enter a number.';
        }
        if (number < min || number > max) {
            return `Enter a value between ${min} and ${max}.`;
        }
        return '';
    };

    const commit = (index: number) => {
        if (!dirty[index]) return;
        errors[index] = validate(index);
        if (errors[index]) return;
        const number = Number(drafts[index]);
        dirty[index] = false;
        if (number === (index === 0 ? value.min : value.max)) return;
        drafts[index] = String(number);
        pending = index === 0 ? [number, value.max] : [value.min, number];
        onValueCommit(pending);
    };

    const handleKeyDown = (event: KeyboardEvent, index: number) => {
        if (event.isComposing) return;
        if (event.key !== 'Enter' && event.key !== 'Escape') return;
        event.preventDefault();
        event.stopPropagation();
        if (event.key === 'Escape') reset();
        else commit(index);
    };
</script>

<div class="flex gap-2">
    {#each ['Min', 'Max'] as endpoint, index}
        <div class="min-w-0 flex-1">
            <label for="{id}-{index}" class="text-xs text-diffuse-foreground">{endpoint}</label>
            <div class="flex items-center gap-1">
                <Input
                    id="{id}-{index}"
                    type="text"
                    inputmode={integer ? 'numeric' : 'decimal'}
                    aria-label="{label} {index === 0 ? 'minimum' : 'maximum'}"
                    aria-invalid={!!errors[index]}
                    aria-describedby={errors[index] ? `${id}-${index}-error` : undefined}
                    class="h-8 px-2"
                    wrapperClass="min-w-0 flex-1"
                    bind:value={drafts[index]}
                    oninput={() => (dirty[index] = true)}
                    onblur={() => commit(index)}
                    onkeydown={(event) => handleKeyDown(event, index)}
                />
                {#if unit}<span class="text-xs text-diffuse-foreground">{unit}</span>{/if}
            </div>
            {#if errors[index]}
                <p id="{id}-{index}-error" role="alert" class="text-xs text-destructive">
                    {errors[index]}
                </p>
            {/if}
        </div>
    {/each}
</div>
