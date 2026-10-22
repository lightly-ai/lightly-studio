import { flushSync } from 'svelte';
import { writable, type Writable } from 'svelte/store';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAssistedLabelingTools } from './useAssistedLabelingTools.svelte';

const mocks = vi.hoisted(() => ({
    context: { status: 'smart-select' as string, panFrom: undefined as string | undefined },
    status: { disabledReason: null as string | null },
    isEditingMode: undefined as unknown as Writable<boolean>
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

let cleanup = () => {};

const setup = () => {
    const context = $state<typeof mocks.context>({ status: 'smart-select', panFrom: undefined });
    const status = $state<typeof mocks.status>({ disabledReason: null });
    mocks.context = context;
    mocks.status = status;
    mocks.isEditingMode = writable(true);
    let tools!: ReturnType<typeof useAssistedLabelingTools>;
    cleanup = $effect.root(() => {
        tools = useAssistedLabelingTools();
    });
    flushSync();
    return { context, status, tools };
};

describe('useAssistedLabelingTools', () => {
    afterEach(() => cleanup());

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
        tools.state.smartSelect = { ...tools.state.smartSelect, canSave: true };

        context.status = 'drag';
        flushSync();
        expect(tools.activeTool).toBeNull();
        expect(tools.isPanning).toBe(false);
        expect(tools.state.smartSelect.canSave).toBe(false);
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
});
