<script lang="ts">
    import { samplingGoals, unavailableReasons, type SamplingGoal } from './samplingGoals';
    import SamplingGoalSettings from './SamplingGoalSettings.svelte';
    import SamplingOutputMock from './SamplingOutputMock.svelte';

    interface Props {
        showUnavailable?: boolean;
    }

    let { showUnavailable = true }: Props = $props();
    let selectedGoal = $state<SamplingGoal>('diverse');
    let settingsRevision = $state(0);
    const selected = $derived(samplingGoals.find((goal) => goal.id === selectedGoal)!);
</script>

<div
    class="mx-auto max-w-5xl rounded-xl border border-border bg-background p-5 text-foreground shadow-sm"
>
    <div class="mb-5 space-y-1">
        <p class="text-xs font-semibold uppercase tracking-wide text-primary">Sampling concept</p>
        <h2 class="text-xl font-semibold">What would you like to select?</h2>
        <p class="text-sm text-muted-foreground">
            Choose a goal to see the settings you would use. This is a UI preview; it does not
            create a selection.
        </p>
    </div>

    <div class="grid gap-5 md:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div class="grid gap-2" role="group" aria-label="Sampling goals">
            {#each samplingGoals as goal (goal.id)}
                {@const reason = showUnavailable ? unavailableReasons[goal.id] : undefined}
                <button
                    type="button"
                    disabled={!!reason}
                    aria-pressed={selectedGoal === goal.id}
                    onclick={() => (selectedGoal = goal.id)}
                    class="rounded-lg border px-4 py-3 text-left transition-colors {selectedGoal ===
                    goal.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'} {reason
                        ? 'cursor-not-allowed opacity-60'
                        : ''}"
                >
                    <span class="block text-sm font-semibold">{goal.title}</span>
                    <span class="mt-1 block text-xs leading-relaxed text-muted-foreground">
                        {goal.description}
                    </span>
                    {#if reason}
                        <span class="mt-2 block text-xs font-medium text-muted-foreground">
                            Unavailable: {reason}
                        </span>
                    {/if}
                </button>
            {/each}
        </div>

        <div class="h-fit rounded-lg border border-border bg-muted/30 p-5">
            <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Your choice
            </p>
            <h3 class="mt-1 text-lg font-semibold">{selected.title}</h3>
            <p class="mt-2 text-sm text-muted-foreground">{selected.description}</p>
            <div class="mt-5 border-t border-border pt-5">
                <SamplingGoalSettings
                    goal={selectedGoal}
                    onSettingsChange={() => settingsRevision++}
                />
            </div>
            <SamplingOutputMock
                goalTitle={selected.title}
                isDeduplication={selectedGoal === 'deduplicate'}
                configurationKey={`${selectedGoal}:${settingsRevision}`}
            />
        </div>
    </div>
</div>
