import { getContext, setContext } from 'svelte';

export type BrushMode = 'brush' | 'eraser';
export type ToolbarStatus = 'bounding-box' | 'brush' | 'eraser' | 'drag' | 'cursor';

export type SampleDetailsToolbarContext = {
    status: ToolbarStatus;
    brush: {
        mode: BrushMode;
        size: number;
    };
};

const CONTEXT_KEY = 'sample-details-toolbar-type';

export function createSampleDetailsToolbarContext(
    initiaValue: SampleDetailsToolbarContext = {
        status: 'cursor',
        brush: { mode: 'brush', size: 50 }
    }
): SampleDetailsToolbarContext {
    const existingContext = getContext<SampleDetailsToolbarContext | undefined>(CONTEXT_KEY);
    if (existingContext) {
        return existingContext;
    }

    const context: SampleDetailsToolbarContext = $state(initiaValue);
    setContext(CONTEXT_KEY, context);
    return context;
}

export function useSampleDetailsToolbarContext(): {
    context: SampleDetailsToolbarContext;
    setBrushMode: (mode: BrushMode) => void;
    setBrushSize: (size: number) => void;
    setStatus: (status: ToolbarStatus) => void;
} {
    const context = getContext<SampleDetailsToolbarContext>(CONTEXT_KEY);

    if (!context) {
        throw new Error('SampleDetailsToolbarContext not found');
    }

    function setBrushMode(mode: BrushMode) {
        context.brush.mode = mode;
    }

    function setBrushSize(size: number) {
        context.brush.size = size;
    }

    function setStatus(status: ToolbarStatus) {
        context.status = status;
    }

    return { context, setBrushMode, setBrushSize, setStatus };
}
