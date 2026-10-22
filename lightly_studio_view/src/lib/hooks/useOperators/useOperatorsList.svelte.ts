import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import {
    getOperatorsOptions,
    getOperatorsQueryKey,
    reloadOperatorsMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';

/**
 * Lists the registered operators. `reload` asks the server to register the plugins that were
 * installed after it started, for example with `pip install` in a terminal.
 */
export const useOperatorsList = () => {
    const client = useQueryClient();
    const query = createQuery(() => getOperatorsOptions());
    const reloadMutation = createMutation(() => ({
        ...reloadOperatorsMutation(),
        onSuccess: (operators) => client.setQueryData(getOperatorsQueryKey(), operators)
    }));

    return { query, reloadMutation, reload: () => reloadMutation.mutate({}) };
};
