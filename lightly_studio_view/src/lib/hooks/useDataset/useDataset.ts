import { readDataset, SampleType } from '$lib/api/lightly_studio_local';

export const useDataset = (datasetId: string) => {
    const get_details = async (): Promise<{ sampleType: SampleType } | null> => {
        const { data } = await readDataset({
            path: { dataset_id: datasetId }
        });
        if (!data) return null;

        return {
            sampleType: data.sample_type
        };
    };

    return {
        get_details
    };
};
