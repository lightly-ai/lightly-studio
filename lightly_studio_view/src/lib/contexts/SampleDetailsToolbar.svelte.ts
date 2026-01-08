import { getContext, setContext } from 'svelte';

export type SampleDetailsToolbarContext = {
    status: 'bounding-box' | 'eraser' | 'settigs' | 'none';
};

const CONTEXT_KEY = 'sample-details-toolbar-type';

export function createSampleDetailsToolbarContext(
    initiaValue: SampleDetailsToolbarContext = { status: 'none' }
): SampleDetailsToolbarContext {
    const context: SampleDetailsToolbarContext = $state(initiaValue);

    setContext(CONTEXT_KEY, context);
    return context;
}

export function useSampleDetailsToolbarContext(): SampleDetailsToolbarContext {
    const context = getContext<SampleDetailsToolbarContext>(CONTEXT_KEY);

    if (!context) {
        throw new Error('SampleDetailsToolbarContext not found');
    }

    return context;
}
