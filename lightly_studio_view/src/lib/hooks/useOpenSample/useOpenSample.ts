import { readonly, writable } from 'svelte/store';

// Details view URL of the sample last open on each tab, keyed by collection id. In memory
// only, so it lasts for the session.
const openSampleHrefs = writable<Record<string, string>>({});

/**
 * Remembers which sample is open in the details view of each tab, so switching tabs and back
 * reopens it. The details routes set it, and opening the grid of the tab clears it.
 */
export function useOpenSample() {
    const rememberOpenSample = (collectionId: string, href: string) => {
        openSampleHrefs.update((hrefs) => ({ ...hrefs, [collectionId]: href }));
    };

    const forgetOpenSample = (collectionId: string) => {
        openSampleHrefs.update((hrefs) => {
            if (!(collectionId in hrefs)) return hrefs;
            const next = { ...hrefs };
            delete next[collectionId];
            return next;
        });
    };

    return {
        openSampleHrefs: readonly(openSampleHrefs),
        rememberOpenSample,
        forgetOpenSample
    };
}
