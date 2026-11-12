import { getContext, setContext } from 'svelte';

const KEY = Symbol('metadata-field-search');

/** Lets every field header below highlight the current field search. */
export const setFieldSearchContext = (getSearch: () => string): void => {
    setContext(KEY, getSearch);
};

/** Returns the current field search, or an empty search outside a search context. */
export const getFieldSearchContext = (): (() => string) =>
    getContext<(() => string) | undefined>(KEY) ?? (() => '');
