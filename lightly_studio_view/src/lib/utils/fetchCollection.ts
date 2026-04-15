import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';
import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';

export async function fetchCollection(collection_id: string): Promise<CollectionViewWithCount> {
    try {
        const { data } = await readCollection({
            path: { collection_id }
        });

        if (!data) {
            throw new Error(`Collection data is undefined for collection_id: ${collection_id}`);
        }

        return data;
    } catch (error) {
        throw new Error(
            `Collection ${collection_id} not found` +
                (error instanceof Error ? `: ${error.message}` : '')
        );
    }
}
