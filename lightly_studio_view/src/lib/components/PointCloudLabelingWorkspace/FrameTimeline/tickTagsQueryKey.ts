/**
 * A partial query key that matches the frame tag queries of every sequence. Use with
 * `queryClient.invalidateQueries` after frame tags change.
 */
export const TICK_TAGS_QUERY_KEY = [{ _id: 'getTickTags' }];
