import type { CollectionView } from '$lib/api/lightly_studio_local';
import { readCollectionHierarchy } from '$lib/api/lightly_studio_local/sdk.gen';

export async function fetchCollectionHierarchy(dataset_id: string): Promise<CollectionView[]> {
    try {
        const { data: hierarchyData } = await readCollectionHierarchy({
            path: { collection_id: dataset_id }
        });
        return hierarchyData || [];
    } catch (err) {
        if (err && typeof err === 'object' && 'status' in err) {
            throw err;
        }
        const errorMessage = err instanceof Error ? err.message : String(err);
        throw new Error(`Error loading collection hierarchy: ${errorMessage}`);
    }
}
