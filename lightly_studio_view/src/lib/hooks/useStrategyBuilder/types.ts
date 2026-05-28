export type StrategyType =
    | 'diversity'
    | 'typicality'
    | 'similarity'
    | 'metadata_weighting'
    | 'class_balancing';

export const STRATEGY_OPTIONS: { type: StrategyType; label: string; description: string }[] = [
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
