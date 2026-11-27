export const samplingGoals = [
    {
        id: 'diverse',
        title: 'Select a diverse subset',
        description:
            'Cover different kinds of samples. Rare or unusual samples may receive extra attention.'
    },
    {
        id: 'representative',
        title: 'Diverse and representative',
        description:
            'Select a diverse subset that aims to reflect the dataset’s mix. Exact proportions are not guaranteed.'
    },
    {
        id: 'deduplicate',
        title: 'Remove near-duplicates',
        description:
            'Keep sufficiently distinct images. The result may contain fewer than the maximum you set.'
    },
    {
        id: 'similar',
        title: 'Find more like my examples',
        description: 'Choose a tag containing examples to look for.'
    },
    {
        id: 'balance',
        title: 'Balance my subset',
        description: 'Aim for a chosen mix of annotation classes or metadata values.'
    },
    {
        id: 'numeric',
        title: 'Select by a numeric value',
        description: 'Choose higher or lower values, such as confidence or sharpness.'
    },
    {
        id: 'typical',
        title: 'Select typical examples',
        description: 'Prefer samples that resemble many others.'
    },
    {
        id: 'outliers',
        title: 'Find outliers',
        description: 'Surface rare or unusual samples, such as edge cases or anomalies.'
    }
] as const;

export type SamplingGoal = (typeof samplingGoals)[number]['id'];

export const unavailableReasons: Partial<Record<SamplingGoal, string>> = {
    similar: 'Create a sample tag with example images to enable this choice.',
    balance: 'Add annotations or categorical metadata to enable this choice.',
    numeric: 'Index a numeric metadata field to enable this choice.'
};
