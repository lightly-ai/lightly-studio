export interface DiversityParams {
    strength: number;
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

export type ClassBalancingAnnotationSource = 'uniform' | 'input' | 'dictionary';

export interface ClassBalancingParams {
    annotation_source: ClassBalancingAnnotationSource;
    target_distribution: ClassBalancingTargetRow[];
    strength: number;
}

interface StrategyParamsByType {
    diversity: DiversityParams;
    typicality: TypicalityParams;
    similarity: SimilarityParams;
    metadata_weighting: MetadataWeightingParams;
    class_balancing: ClassBalancingParams;
}

export type StrategyInstance = {
    [K in StrategyType]: {
        id: string;
        type: K;
        params: StrategyParamsByType[K];
        isExpanded: boolean;
    };
}[StrategyType];

export type StrategyParams = StrategyInstance['params'];

export const STRATEGY_OPTIONS = [
    {
        type: 'diversity',
        label: 'Diversity',
        description:
            'Selects samples spread across the embedding space. Use to reduce redundancy and build varied training sets.'
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
];

export type StrategyType = (typeof STRATEGY_OPTIONS)[number]['type'];
