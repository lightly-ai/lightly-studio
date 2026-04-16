import { createQuery } from '@tanstack/svelte-query';
import { getQuerySchema } from '$lib/api/lightly_studio_local';

export interface FieldSchema {
    name: string;
    field_type: 'number' | 'string' | 'boolean';
    operators: string[];
}

export interface QuerySchema {
    fields: FieldSchema[];
    subcontexts: Record<string, FieldSchema[]>;
}

export function useQuerySchema(collectionId: string) {
    const schema = createQuery({
        queryKey: ['querySchema', collectionId],
        queryFn: async () => {
            const { data } = await getQuerySchema({
                path: { collection_id: collectionId },
                throwOnError: true
            });
            return data as unknown as QuerySchema;
        },
        staleTime: 5 * 60 * 1000
    });

    return { schema };
}
