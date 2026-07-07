import type { TagView } from '$lib/services/types';
export interface DiversityParams {
    strength: number;
}

export interface DeduplicationParams {
    strength: number;
    stopping_condition_minimum_distance: number;
}

export interface TypicalityParams {
    strength: number;
}

export interface SimilarityParams {
    query_tag_id: string;
    strength: number;
}

export interface MetadataWeightingParams {
    metadata_key: string;
    strength: number;
}

export interface ClassBalancingTargetRow {
    class_name: string;
    weight: number;
}

export type ClassBalancingTargetDistributionMode = 'uniform' | 'input' | 'dictionary';

export interface ClassBalancingParams {
    annotation_source_id: string;
    target_distribution_mode: ClassBalancingTargetDistributionMode;
    target_distribution: ClassBalancingTargetRow[];
    strength: number;
}

export interface StrategyParamsByType {
    diversity: DiversityParams;
    deduplication: DeduplicationParams;
    typicality: TypicalityParams;
    similarity: SimilarityParams;
    metadata_weighting: MetadataWeightingParams;
    class_balancing: ClassBalancingParams;
}

export type StrategyType = keyof StrategyParamsByType;

export type StrategyInstance = {
    [K in keyof StrategyParamsByType]: {
        id: string;
        type: K;
        params: StrategyParamsByType[K];
        isExpanded: boolean;
    };
}[keyof StrategyParamsByType];

export type StrategyParams = StrategyInstance['params'];

export type StrategySummaryTag = Pick<TagView, 'tag_id' | 'name'>;

export const STRATEGY_OPTIONS: { type: StrategyType; label: string; description: string }[] = [
    {
        type: 'diversity',
        label: 'Diversity',
        description:
            'Selects samples spread across the embedding space. Use to reduce redundancy and build varied training sets.'
    },
    {
        type: 'deduplication',
        label: 'Deduplication',
        description:
            'Removes near-duplicates by keeping only samples that are at least a minimum distance apart in embedding space. May select fewer than the requested number of samples.'
    },
    {
        type: 'typicality',
        label: 'Typicality',
        description:
            'Scores samples by how close they are to many others in embedding space - typical samples score high, outliers score low. Use to find the most representative examples in the dataset.'
    },
    {
        type: 'similarity',
        label: 'Similarity',
        description:
            'Selects samples most similar to a reference tag. Use to find more examples like ones you have already identified.'
    },
    {
        type: 'metadata_weighting',
        label: 'Metadata Weighting',
        description:
            'Weights selection by a numeric metadata field. Use to prioritize samples with a specific measured property such as sharpness or confidence.'
    },
    {
        type: 'class_balancing',
        label: 'Class Balancing',
        description:
            'Selects samples to reach a target class distribution using annotation labels. Use to fix class imbalance or enforce custom class proportions.'
    }
] satisfies Array<{ type: StrategyType; label: string; description: string }>;

export const STRATEGY_LABELS: Record<StrategyType, string> = Object.fromEntries(
    STRATEGY_OPTIONS.map((strategy) => [strategy.type, strategy.label])
) as Record<StrategyType, string>;

export const STRATEGY_DEFAULTS: { [K in StrategyType]: StrategyParamsByType[K] } = {
    diversity: { strength: 1 },
    deduplication: { strength: 1, stopping_condition_minimum_distance: 0.1 },
    typicality: { strength: 1 },
    similarity: { query_tag_id: '', strength: 1 },
    metadata_weighting: { metadata_key: '', strength: 1 },
    class_balancing: {
        annotation_source_id: '',
        target_distribution_mode: 'uniform',
        target_distribution: [],
        strength: 1
    }
};
