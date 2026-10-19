<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import { parseTargets } from './AutoLabelDialog.helpers';

    interface Props {
        prompts: string[];
        overrides: Record<string, string>;
    }
    let { prompts = $bindable(), overrides = $bindable() }: Props = $props();
    let text = $state('');
</script>

<div class="grid gap-2">
    <Label for="auto-label-targets">Targets</Label>
    <textarea
        id="auto-label-targets"
        class="min-h-24 w-full rounded border bg-background p-2 text-sm"
        placeholder="person, bicycle, car"
        bind:value={text}
        oninput={() => (prompts = parseTargets(text))}
    ></textarea>
    <p class="text-xs text-muted-foreground">
        {prompts.length} targets ≈ {prompts.length} model calls per image
    </p>
    {#if prompts.length}
        <details>
            <summary class="cursor-pointer text-sm">Override annotation classes</summary>
            <div class="mt-2 grid gap-2">
                {#each prompts as prompt, index (prompt)}
                    <div class="grid grid-cols-2 items-center gap-2">
                        <Label for={`auto-class-${index}`} class="break-words">{prompt}</Label>
                        <Input
                            id={`auto-class-${index}`}
                            placeholder={prompt}
                            value={overrides[prompt] ?? ''}
                            oninput={(event) => {
                                overrides = { ...overrides, [prompt]: event.currentTarget.value };
                            }}
                        />
                    </div>
                {/each}
            </div>
        </details>
    {/if}
</div>
