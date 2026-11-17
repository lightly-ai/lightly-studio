import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'svelte';
import type { beforeNavigate } from '$app/navigation';
import ModelSuggestionGuard from './ModelSuggestionGuard.svelte';

const mocks = vi.hoisted(() => ({
    navigate: undefined as unknown as Parameters<typeof beforeNavigate>[0],
    goto: vi.fn(),
    toastInfo: vi.fn()
}));

vi.mock('$app/navigation', () => ({
    beforeNavigate: (callback: typeof mocks.navigate) => {
        mocks.navigate = callback;
    },
    goto: mocks.goto
}));
vi.mock('svelte-sonner', () => ({ toast: { info: mocks.toastInfo } }));

type GuardState = ComponentProps<typeof ModelSuggestionGuard>['labelWithModel'];
type MutableGuardState = { -readonly [K in keyof GuardState]: GuardState[K] };

const setup = () => {
    const labelWithModel = $state<MutableGuardState>({
        isSaving: false,
        isGenerating: false,
        predictions: [
            {
                class_name: 'cat',
                bbox: { x: 0, y: 0, width: 10, height: 10 },
                segmentation_mask: null,
                score: 0.9
            }
        ],
        pendingChange: null,
        requestChange: (action) => {
            labelWithModel.pendingChange = action;
        },
        clear: vi.fn(() => {
            labelWithModel.predictions = [];
        }),
        confirmChange: () => {
            const action = labelWithModel.pendingChange;
            labelWithModel.pendingChange = null;
            action?.();
        },
        cancelChange: () => {
            labelWithModel.pendingChange = null;
        }
    });
    render(ModelSuggestionGuard, { labelWithModel });
    const navigation = {
        from: null,
        to: {
            url: new URL('http://localhost/images/next'),
            params: {},
            route: { id: null },
            scroll: null
        },
        type: 'goto' as const,
        willUnload: false,
        cancel: vi.fn(),
        complete: Promise.resolve()
    };
    return { labelWithModel, navigation };
};

describe('ModelSuggestionGuard', () => {
    beforeEach(() => vi.clearAllMocks());

    it('keeps the draft when navigation is canceled and navigates after confirmation', async () => {
        const { labelWithModel, navigation } = setup();
        mocks.navigate(navigation);
        await fireEvent.click(await screen.findByRole('button', { name: 'Keep reviewing' }));
        expect(navigation.cancel).toHaveBeenCalledOnce();
        expect(labelWithModel.predictions).toHaveLength(1);
        expect(mocks.goto).not.toHaveBeenCalled();

        mocks.navigate(navigation);
        await fireEvent.click(await screen.findByRole('button', { name: 'Discard and continue' }));
        expect(labelWithModel.clear).toHaveBeenCalledOnce();
        expect(mocks.goto).toHaveBeenCalledWith(navigation.to.url);
    });

    it('blocks navigation during a save and lets the browser confirm document unloads', () => {
        const { labelWithModel, navigation } = setup();
        labelWithModel.isSaving = true;
        mocks.navigate(navigation);
        expect(mocks.toastInfo).toHaveBeenCalledOnce();
        expect(labelWithModel.pendingChange).toBeNull();
        labelWithModel.isSaving = false;
        mocks.navigate({ ...navigation, type: 'leave', willUnload: true, to: null });
        expect(navigation.cancel).toHaveBeenCalledTimes(2);
        expect(labelWithModel.pendingChange).toBeNull();
    });
});
