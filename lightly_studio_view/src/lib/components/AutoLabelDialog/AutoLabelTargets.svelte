<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    interface Props {
        classes?: string[] | null;
        prompts: string[];
        overrides: Record<string, string>;
    }
    let { classes, prompts = $bindable(), overrides = $bindable() }: Props = $props();
    let text = $state('');
</script>

<div class="grid gap-2">
    <Label for="auto-label-targets">Targets</Label>
    {#if classes}
        <div id="auto-label-targets" class="max-h-32 overflow-auto rounded border p-2">
            {#each classes as name (name)}
                <label class="flex items-center gap-2 py-1 text-sm">
                    <input type="checkbox" value={name} bind:group={prompts} />{name}
                </label>
            {/each}
        </div>
    {:else}
        <textarea
            id="auto-label-targets"
            class="min-h-24 w-full rounded border bg-background p-2 text-sm"
            placeholder="person, bicycle, car"
            bind:value={text}
            oninput={() => {
                prompts = [
                    ...new Set(
                        text
                            .split(/[,\n]/)
                            .map((p) => p.trim())
                            .filter(Boolean)
                    )
                ];
            }}
        ></textarea>
    {/if}
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
