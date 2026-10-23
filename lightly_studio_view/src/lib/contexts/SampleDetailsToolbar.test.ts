import { expect, it, vi } from 'vitest';
import {
    createSampleDetailsToolbarContext,
    isAssistedLabelingStatus,
    useSampleDetailsToolbarContext
} from './SampleDetailsToolbar.svelte';

const contexts = vi.hoisted(() => new Map());
vi.mock('svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('svelte')>()),
    getContext: (key: string) => contexts.get(key),
    setContext: (key: string, value: unknown) => contexts.set(key, value)
}));

it('initializes and reuses toolbar state and applies tool settings', () => {
    expect(() => useSampleDetailsToolbarContext()).toThrow('SampleDetailsToolbarContext not found');
    const context = createSampleDetailsToolbarContext();
    expect(context.slic).toEqual({ level: 'medium', status: 'idle' });
    expect(createSampleDetailsToolbarContext()).toBe(context);
    const toolbar = useSampleDetailsToolbarContext();
    toolbar.setSlicLevel('fine');
    toolbar.setSlicStatus('computing');
    toolbar.setStatus('slic');
    toolbar.setBrushMode('eraser');
    toolbar.setBrushSize(25);
    expect(context).toEqual({
        status: 'slic',
        slic: { level: 'fine', status: 'computing' },
        brush: { mode: 'eraser', size: 25 }
    });
});

it('tells the assisted labeling statuses apart', () => {
    expect(isAssistedLabelingStatus('smart-select')).toBe(true);
    expect(isAssistedLabelingStatus('brush')).toBe(false);
});
