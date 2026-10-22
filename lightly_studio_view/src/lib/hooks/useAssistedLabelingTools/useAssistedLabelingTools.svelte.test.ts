import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAssistedLabelingTools } from './useAssistedLabelingTools.svelte';

const mocks = vi.hoisted(() => ({
    context: { status: 'smart-select' as string }
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/contexts/SampleDetailsToolbar.svelte')>()),
    useSampleDetailsToolbarContext: () => ({
        context: mocks.context,
        setStatus: (status: string) => (mocks.context.status = status)
    })
}));
vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ context: { annotationLabel: null } })
}));
vi.mock('$lib/hooks/useAssistedLabelingStatus', () => ({
    useAssistedLabelingStatus: () => ({ disabledReason: null })
}));

let cleanup = () => {};

describe('useAssistedLabelingTools', () => {
    afterEach(() => cleanup());

    it('keeps the tool active while panning', () => {
        const context = $state({ status: 'smart-select' });
        mocks.context = context;
        let tools!: ReturnType<typeof useAssistedLabelingTools>;
        cleanup = $effect.root(() => {
            tools = useAssistedLabelingTools();
        });
        flushSync();

        context.status = 'drag';
        flushSync();
        expect(tools.activeTool).toBe('smart-select');
        expect(tools.isPanning).toBe(true);

        context.status = 'cursor';
        flushSync();
        expect(tools.activeTool).toBeNull();
        expect(tools.isPanning).toBe(false);
    });
});
