import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAssistedLabelingTools } from './useAssistedLabelingTools.svelte';

const mocks = vi.hoisted(() => ({
    context: { status: 'find-instances' as string },
    tools: {
        smartSelectDisabledReason: null,
        instancesDisabledReason: null,
        maxInstances: 32,
        defaultMaxInstances: 16
    }
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({
        context: mocks.context,
        setStatus: (status: string) => (mocks.context.status = status)
    })
}));
vi.mock('$lib/hooks/useAssistedLabelingProvider', () => ({
    useAssistedLabelingProvider: () => ({ tools: mocks.tools })
}));

let cleanup = () => {};

describe('useAssistedLabelingTools', () => {
    afterEach(() => cleanup());

    it('ends box drawing when the find all instances tool is left', () => {
        const context = $state({ status: 'find-instances' });
        mocks.context = context;
        let tools!: ReturnType<typeof useAssistedLabelingTools>;
        cleanup = $effect.root(() => {
            tools = useAssistedLabelingTools();
        });
        flushSync();
        tools.state.isDrawingInstancesBox = true;
        flushSync();
        expect(tools.state.isDrawingInstancesBox).toBe(true);

        context.status = 'cursor';
        flushSync();

        expect(tools.state.isDrawingInstancesBox).toBe(false);
    });
});
