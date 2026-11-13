<script lang="ts">
    import { cn } from '$lib/utils/shadcn';
    import { SAMPLING_GOALS, type SamplingGoalId } from '../samplingGoals';

    interface Props {
        selectedGoalId: SamplingGoalId;
        unavailableReasons?: Partial<Record<SamplingGoalId, string>>;
        onSelect: (goalId: SamplingGoalId) => void;
    }

    let { selectedGoalId, unavailableReasons = {}, onSelect }: Props = $props();
</script>

<div class="grid gap-2" role="radiogroup" aria-label="Sampling goal">
    {#each SAMPLING_GOALS as goal (goal.id)}
        {@const reason = unavailableReasons[goal.id]}
        <button
            type="button"
            role="radio"
            aria-checked={selectedGoalId === goal.id}
            disabled={!!reason}
            title={reason}
            data-testid="sampling-goal-{goal.id}"
            onclick={() => onSelect(goal.id)}
            class={cn(
                'flex items-start gap-2.5 rounded-md border p-2.5 text-left transition-colors',
                selectedGoalId === goal.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50',
                reason && 'cursor-not-allowed opacity-50'
            )}
        >
            <goal.icon class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span class="min-w-0">
                <span class="block text-sm font-medium text-foreground">{goal.title}</span>
                <span class="block text-xs leading-snug text-muted-foreground">
                    {reason ?? goal.description}
                </span>
            </span>
        </button>
    {/each}
</div>
