<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { untrack } from 'svelte';

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

    const reset = (preserve = false) => {
        drafts = [value.min, value.max].map((n, i) =>
            preserve && dirty[i] ? drafts[i] : String(n)
        );
        if (!preserve) {
            dirty = [false, false];
            errors = ['', ''];
        }
    };
    $effect(() => {
        const acknowledged = [value.min, value.max].every((n, i) => n === pending?.[i]);
        pending = undefined;
        untrack(() => reset(acknowledged));
    });

    const validate = (index: number, range: number[]): string => {
        const number = drafts[index].trim() ? Number(drafts[index]) : NaN;
        const min = index === 0 ? bound.min : range[0];
        const max = index === 0 ? range[1] : bound.max;
        if (!Number.isFinite(number) || (integer && !Number.isInteger(number))) {
            return integer ? 'Enter a whole number.' : 'Enter a number.';
        }
        return number < min || number > max ? `Enter a value between ${min} and ${max}.` : '';
    };

    const commit = (index: number) => {
        if (!dirty[index]) return;
        const range = pending ?? [value.min, value.max];
        errors[index] = validate(index, range);
        if (errors[index]) return;
        const number = Number(drafts[index]);
        dirty[index] = false;
        if (number === range[index]) return;
        drafts[index] = String(number);
        pending = range.map((n, i) => (i === index ? number : n));
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
