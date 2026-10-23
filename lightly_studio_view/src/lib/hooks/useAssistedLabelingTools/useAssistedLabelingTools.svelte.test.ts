import { flushSync } from 'svelte';
import { writable, type Writable } from 'svelte/store';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAssistedLabelingTools } from './useAssistedLabelingTools.svelte';

const mocks = vi.hoisted(() => ({
    context: { status: 'smart-select' as string, panFrom: undefined as string | undefined },
    status: { disabledReason: null as string | null },
    isEditingMode: undefined as unknown as Writable<boolean>,
    clearSmartSelect: vi.fn(),
    clearInstances: vi.fn()
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
    useAssistedLabelingStatus: () => mocks.status
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ isEditingMode: mocks.isEditingMode })
}));
vi.mock('$lib/components/SampleDetails/SmartSelectOverlay/useSmartSelect.svelte', () => ({
    useSmartSelect: () => ({ clear: mocks.clearSmartSelect })
}));
vi.mock('$lib/components/SampleDetails/FindInstancesOverlay/useFindInstances.svelte', () => ({
    useFindInstances: () => ({ clear: mocks.clearInstances })
}));

let cleanup = () => {};

const setup = (initialStatus = 'smart-select') => {
    const context = $state<typeof mocks.context>({ status: initialStatus, panFrom: undefined });
    const status = $state<typeof mocks.status>({ disabledReason: null });
    mocks.context = context;
    mocks.status = status;
    mocks.isEditingMode = writable(true);
    let tools!: ReturnType<typeof useAssistedLabelingTools>;
    cleanup = $effect.root(() => {
        tools = useAssistedLabelingTools(() => ({
            collectionId: 'collection-1',
            sampleId: 'sample-1',
            refetch: vi.fn()
        }));
    });
    flushSync();
    return { context, status, tools };
};

describe('useAssistedLabelingTools', () => {
    afterEach(() => {
        cleanup();
        vi.clearAllMocks();
    });

    it('keeps the tool active while Space panning', () => {
        const { context, tools } = setup();

        context.panFrom = 'smart-select';
        context.status = 'drag';
        flushSync();
        expect(tools.activeTool).toBe('smart-select');
        expect(tools.isPanning).toBe(true);
    });

    it('drops the tool for the hand tool', () => {
        const { context, tools } = setup();
        expect(mocks.clearSmartSelect).not.toHaveBeenCalled();

        context.status = 'drag';
        flushSync();
        expect(tools.activeTool).toBeNull();
        expect(tools.isPanning).toBe(false);
        expect(mocks.clearSmartSelect).toHaveBeenCalledOnce();
    });

    it('falls back to the cursor tool when edit mode ends or the tool is disabled', () => {
        const { context, status } = setup();

        mocks.isEditingMode.set(false);
        flushSync();
        expect(context.status).toBe('cursor');

        mocks.isEditingMode.set(true);
        context.status = 'smart-select';
        status.disabledReason = 'missing key';
        flushSync();
        expect(context.status).toBe('cursor');
    });

    it('ends box drawing and drops the results when the find all instances tool is left', () => {
        const { context, tools } = setup('find-instances');
        tools.state.isDrawingInstancesBox = true;
        flushSync();
        expect(tools.state.isDrawingInstancesBox).toBe(true);
        expect(mocks.clearInstances).not.toHaveBeenCalled();

        context.status = 'cursor';
        flushSync();

        expect(tools.state.isDrawingInstancesBox).toBe(false);
        expect(mocks.clearInstances).toHaveBeenCalledOnce();
    });
});
