import { readRootDataset, SampleType, type DatasetView } from '$lib/api/lightly_studio_local';

export const useRootDataset = async (): Promise<DatasetView> => {
    const { data } = await readRootDataset();
    
    if (!data) 
        throw "No dataset found"

    return data
};
