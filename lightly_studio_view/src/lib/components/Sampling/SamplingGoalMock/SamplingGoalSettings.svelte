<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import type { SamplingGoal } from './samplingGoals';

    interface Props {
        goal: SamplingGoal;
        onSettingsChange: () => void;
    }

    let { goal, onSettingsChange }: Props = $props();
    let diversityBasedOn = $state('scenes');
    let balanceBy = $state('classes');
    let numericPreference = $state('higher');

    const selectClass =
        'mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground';
</script>

<section
    class="space-y-4"
    aria-label="Choice settings"
    oninput={onSettingsChange}
    onchange={onSettingsChange}
>
    {#if goal === 'diverse' || goal === 'representative'}
        <label class="block text-sm font-medium text-foreground">
            Diversity based on
            <select class={selectClass} bind:value={diversityBasedOn}>
                <option value="scenes">Scenes</option>
                <option value="objects">Annotated objects</option>
            </select>
        </label>
        {#if diversityBasedOn === 'objects'}
            <p class="text-xs text-muted-foreground">
                Uses annotated objects to find variety, then returns whole images. Object detection
                or segmentation annotations are required.
            </p>
        {/if}
        {#if goal === 'diverse'}
            <p class="text-xs text-muted-foreground">
                A diverse subset may not reflect the original distribution. Choose “Diverse and
                representative” if that mix matters.
            </p>
        {:else}
            <p class="text-xs text-muted-foreground">
                This preset combines diversity and typicality. It aims to reflect the dataset’s mix;
                exact proportions are not guaranteed.
            </p>
        {/if}
    {:else if goal === 'deduplicate'}
        <label class="block text-sm font-medium text-foreground">
            Minimum distance between images
            <Input wrapperClass="mt-1" type="number" min="0" max="1" step="0.01" value={0.2} />
        </label>
        <p class="text-xs text-muted-foreground">
            A higher distance removes more near-duplicates and usually keeps fewer images.
        </p>
    {:else if goal === 'similar'}
        <label class="block text-sm font-medium text-foreground">
            Example tag
            <select class={selectClass}>
                <option>Interesting examples</option>
                <option>Already reviewed</option>
            </select>
        </label>
        <p class="text-xs text-muted-foreground">
            These examples guide the search; they are not automatically included in the result.
        </p>
    {:else if goal === 'balance'}
        <label class="block text-sm font-medium text-foreground">
            Balance by
            <select class={selectClass} bind:value={balanceBy}>
                <option value="classes">Annotation classes</option>
                <option value="metadata">Metadata values</option>
            </select>
        </label>
        {#if balanceBy === 'metadata'}
            <label class="block text-sm font-medium text-foreground">
                Metadata field
                <select class={selectClass}
                    ><option>Location</option><option>Weather</option></select
                >
            </label>
        {:else}
            <label class="block text-sm font-medium text-foreground">
                Annotation source
                <select class={selectClass}
                    ><option>Ground truth</option><option>Predictions</option></select
                >
            </label>
        {/if}
        <p class="text-xs text-muted-foreground">Aim for an even mix across the chosen values.</p>
    {:else if goal === 'numeric'}
        <label class="block text-sm font-medium text-foreground">
            Numeric field
            <select class={selectClass}
                ><option>Confidence</option><option>Sharpness</option></select
            >
        </label>
        <fieldset class="space-y-2 text-sm font-medium text-foreground">
            <legend>Prefer</legend>
            <div class="flex gap-2">
                <label
                    class="flex cursor-pointer items-center gap-2 rounded-md border border-input bg-background px-3 py-2"
                >
                    <input
                        type="radio"
                        name="numeric-preference"
                        value="higher"
                        bind:group={numericPreference}
                        class="accent-primary"
                    />
                    Higher values
                </label>
                <label
                    class="flex cursor-pointer items-center gap-2 rounded-md border border-input bg-background px-3 py-2"
                >
                    <input
                        type="radio"
                        name="numeric-preference"
                        value="lower"
                        bind:group={numericPreference}
                        class="accent-primary"
                    />
                    Lower values
                </label>
            </div>
        </fieldset>
    {:else}
        <p class="text-xs text-muted-foreground">
            {goal === 'typical'
                ? 'Select samples that resemble many others in the dataset.'
                : 'Select rare or unusual samples that differ from most of the dataset.'}
        </p>
    {/if}
</section>
