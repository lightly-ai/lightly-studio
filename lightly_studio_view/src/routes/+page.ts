import { routeHelpers } from '$lib/routes';
import { redirect } from '@sveltejs/kit';
import { SampleType } from '$lib/api/lightly_studio_local';
import { useRootDataset } from '$lib/hooks/useRootDataset/useRootDataset';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

export const load = async () => {
    const dataset = await useRootDataset();

    const { updateRootDataset } = useGlobalStorage();

    updateRootDataset(dataset);

    const route = () => {
        switch (dataset.sample_type) {
            case SampleType.VIDEO:
                return routeHelpers.toVideos(dataset.dataset_id);
            default:
                return routeHelpers.toSamples(dataset.dataset_id);
        }
    };

    redirect(307, route());
};
