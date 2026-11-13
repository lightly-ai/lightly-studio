import { AlertTriangle, CopyMinus, Scale, Search, Shuffle, Tags } from '@lucide/svelte';
import {
    createStrategyInstance,
    type StrategyInstance,
    type StrategyType
} from '$lib/hooks/useStrategyBuilder';

/** The one thing a goal has to ask for before it can run. */
export type GoalInputKind = 'tag' | 'annotation_source' | 'metadata_field';

export const SAMPLING_GOALS = [
    {
        id: 'varied',
        title: 'Varied subset',
        description: 'Cover as many different kinds of image as possible.',
        icon: Shuffle,
        requires: undefined
    },
    {
        id: 'deduplicate',
        title: 'Remove near-duplicates',
        description: 'Keep one image out of each group that looks alike.',
        icon: CopyMinus,
        requires: undefined
    },
    {
        id: 'similar',
        title: 'More like these',
        description: 'Find images that resemble the ones in a tag.',
        icon: Search,
        requires: 'tag'
    },
    {
        id: 'balance',
        title: 'Even out annotation classes',
        description: 'Pick as evenly as possible across the classes.',
        icon: Scale,
        requires: 'annotation_source'
    },
    {
        id: 'balance_metadata',
        title: 'Even out a metadata field',
        description: 'Pick as evenly as possible across the values of one field.',
        icon: Tags,
        requires: 'metadata_field'
    },
    {
        id: 'edge_cases',
        title: 'Find edge cases',
        description: 'Surface rare and unusual images.',
        icon: AlertTriangle,
        requires: undefined
    }
] as const satisfies ReadonlyArray<{
    id: string;
    title: string;
    description: string;
    icon: unknown;
    requires: GoalInputKind | undefined;
}>;

export type SamplingGoalId = (typeof SAMPLING_GOALS)[number]['id'];

/** Relative weight per strategy for each goal. Weights are shares of one mix. */
type StrategyMix = Partial<Record<StrategyType, number>>;

export const GOAL_STRATEGY_MIX: Record<SamplingGoalId, StrategyMix> = {
    // Diversity alone drifts towards outliers, so some typicality holds it back.
    varied: { diversity: 0.8, typicality: 0.2 },
    deduplicate: { deduplication: 1 },
    similar: { similarity: 1 },
    // Balancing alone can pick near-identical images of a rare class.
    balance: { class_balancing: 0.7, diversity: 0.3 },
    balance_metadata: { metadata_balancing: 0.7, diversity: 0.3 },
    // Outliers are the samples that typicality scores lowest.
    edge_cases: { typicality: -1 }
};

export function getGoal(goalId: SamplingGoalId): (typeof SAMPLING_GOALS)[number] {
    return SAMPLING_GOALS.find((goal) => goal.id === goalId)!;
}

/** Builds the strategy instances a goal starts with, filled in with its input. */
export function buildGoalInstances(
    goalId: SamplingGoalId,
    inputValue: string | undefined
): StrategyInstance[] {
    return Object.entries(GOAL_STRATEGY_MIX[goalId]).map(([type, weight]) => {
        const instance = createStrategyInstance(type as StrategyType);
        return withGoalInput(
            { ...instance, params: { ...instance.params, strength: weight } } as StrategyInstance,
            inputValue
        );
    });
}

/** Writes the goal's input into whichever parameter of the strategy needs it. */
export function withGoalInput(
    instance: StrategyInstance,
    inputValue: string | undefined
): StrategyInstance {
    if (inputValue === undefined) return instance;
    const params = instance.params;
    if (instance.type === 'similarity') {
        return { ...instance, params: { ...params, query_tag_id: inputValue } };
    }
    if (instance.type === 'class_balancing' || instance.type === 'subpart_diversity') {
        return {
            ...instance,
            params: { ...params, annotation_source_id: inputValue }
        } as StrategyInstance;
    }
    if (instance.type === 'metadata_balancing') {
        return { ...instance, params: { ...params, metadata_key: inputValue } } as StrategyInstance;
    }
    return instance;
}
