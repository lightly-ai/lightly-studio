<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Typography } from '$lib/components/Typography';
    import type { useAnnotationDetailsEditing } from '../useAnnotationDetailsEditing.svelte';

    type Editing = ReturnType<typeof useAnnotationDetailsEditing>;
    type FieldName = keyof Editing['inputValues'];

    interface Props {
        title: string;
        group: string;
        fields: readonly [FieldName, FieldName, FieldName];
        labels: readonly [string, string, string];
        displayValues: readonly [string, string, string];
        step: number;
        min?: number;
        suffix?: string;
        editable: boolean;
        editing: Editing;
    }

    let {
        title,
        group,
        fields,
        labels,
        displayValues,
        step,
        min,
        suffix = '',
        editable,
        editing
    }: Props = $props();
</script>

<div class="space-y-1">
    <Typography component="dt" variant="body2">{title}</Typography>
    {#if editable}
        <dd class="mt-1 grid grid-cols-3 gap-x-2">
            {#each fields as field, index (field)}
                <div class="flex flex-col gap-0.5">
                    <Typography variant="body2">{labels[index]}</Typography>
                    <Input
                        type="number"
                        {step}
                        {min}
                        aria-label="{group} {labels[index].toLowerCase()}"
                        value={editing.inputValues[field]}
                        oninput={(event) => editing.handleInput(field, event.currentTarget.value)}
                        onfocus={(event) => {
                            editing.handleFocus(field);
                            event.currentTarget.select();
                        }}
                        onblur={() => editing.handleCommit(field)}
                        onkeydown={editing.handleKeyDown}
                        onwheel={(event) => event.preventDefault()}
                    />
                </div>
            {/each}
        </dd>
    {:else}
        <dd class="mt-1 grid grid-cols-3 gap-x-4">
            {#each fields as field, index (field)}
                <Typography variant="body2"
                    >{labels[index]} {displayValues[index]}{suffix}</Typography
                >
            {/each}
        </dd>
    {/if}
</div>
