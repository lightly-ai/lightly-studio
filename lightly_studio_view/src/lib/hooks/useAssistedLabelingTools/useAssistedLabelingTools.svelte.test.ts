import { flushSync } from 'svelte';
import { writable, type Writable } from 'svelte/store';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAssistedLabelingTools } from './useAssistedLabelingTools.svelte';

const mocks = vi.hoisted(() => ({
    context: { status: 'smart-select' as string, panFrom: undefined as string | undefined },
    status: { disabledReason: null as string | null },
    isEditingMode: undefined as unknown as Writable<boolean>,
    clearSmartSelect: vi.fn(),
    clearInstances: vi.fn(),
    getSmartSelectParams: undefined as unknown as () => Record<string, unknown>,
    getInstancesParams: undefined as unknown as () => Record<string, unknown>
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/contexts/SampleDetailsToolbar.svelte')>()),
    useSampleDetailsToolbarContext: () => ({
        context: mocks.context,
        setStatus: (status: string) => (mocks.context.status = status)
    })
}));
vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ context: { annotationLabel: 'person' } })
}));
vi.mock('$lib/hooks/useAssistedLabelingStatus', () => ({
    useAssistedLabelingStatus: () => mocks.status
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ isEditingMode: mocks.isEditingMode })
}));
vi.mock('$lib/components/SampleDetails/SmartSelectOverlay/useSmartSelect.svelte', () => ({
    useSmartSelect: (getParams: () => Record<string, unknown>) => {
        mocks.getSmartSelectParams = getParams;
        return { clear: mocks.clearSmartSelect };
    }
}));
vi.mock('$lib/components/SampleDetails/FindInstancesOverlay/useFindInstances.svelte', () => ({
    useFindInstances: (getParams: () => Record<string, unknown>) => {
        mocks.getInstancesParams = getParams;
        return { clear: mocks.clearInstances };
    }
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

    it('ends box drawing and drops the prompts when the find all instances tool is left', () => {
        const { context, tools } = setup('find-instances');
        tools.state.isDrawingInstancesBox = true;
        tools.state.instancesPrompt = 'cars';
        flushSync();
        expect(tools.state.isDrawingInstancesBox).toBe(true);
        expect(mocks.clearInstances).not.toHaveBeenCalled();

        context.status = 'cursor';
        flushSync();

        expect(tools.state.isDrawingInstancesBox).toBe(false);
        expect(tools.state.instancesPrompt).toBe('');
        expect(mocks.clearInstances).toHaveBeenCalledOnce();
    });

    it('passes the tool settings and falls back to the annotation label as class', () => {
        const { tools } = setup();
        expect(mocks.getSmartSelectParams()).toMatchObject({
            sampleId: 'sample-1',
            annotationClass: 'person'
        });
        expect(mocks.getInstancesParams()).toMatchObject({ annotationClass: 'person' });

        tools.state.smartSelectClass = 'car';
        tools.state.instancesClass = 'bus';
        tools.state.instancesPrompt = 'buses';
        tools.state.maxInstances = 5;
        flushSync();

        expect(tools.smartSelectClass).toBe('car');
        expect(tools.instancesClass).toBe('bus');
        expect(mocks.getSmartSelectParams()).toMatchObject({ annotationClass: 'car' });
        expect(mocks.getInstancesParams()).toMatchObject({
            collectionId: 'collection-1',
            prompt: 'buses',
            maxInstances: 5,
            annotationClass: 'bus'
        });
    });

    it('blocks panning for smart select and while drawing a find instances box', () => {
        const { context, tools } = setup();
        expect(tools.blocksPan).toBe(true);

        context.status = 'find-instances';
        flushSync();
        expect(tools.blocksPan).toBe(false);

        tools.state.isDrawingInstancesBox = true;
        flushSync();
        expect(tools.blocksPan).toBe(true);
    });
});
