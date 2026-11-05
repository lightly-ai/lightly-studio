import { fireEvent, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { useRecentClasses } from '$lib/hooks';
import { usePendingBoxClass } from '$lib/hooks/usePendingBoxClass/usePendingBoxClass';
import PendingBoxCard from './PendingBoxCard.svelte';

const pickClass = vi.hoisted(() => vi.fn());

vi.mock('$lib/hooks/useStickyClass/useStickyClass', async () => {
    const { readable } = await import('svelte/store');
    return { useStickyClass: () => ({ stickyClasses: readable({}), pickClass }) };
});

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: [
            { annotation_label_id: 'l1', annotation_label_name: 'bobcat' },
            { annotation_label_id: 'l2', annotation_label_name: 'coyote' },
            { annotation_label_id: 'l3', annotation_label_name: 'deer' }
        ]
    })
}));

// Seeds a pending request, then renders the card for it.
const setup = (toolbarStatus = 'bounding-box') => {
    const pending = usePendingBoxClass();
    const result = pending.requestClass({ x: 1, y: 2, width: 30, height: 40 });
    render(PendingBoxCard, {
        props: { collectionId: 'col-1', getLayer: () => null },
        context: new Map<string, unknown>([
            ['annotation-label', { isDrawing: false }],
            ['sample-details-toolbar-type', { status: toolbarStatus }]
        ])
    });
    return { result, user: userEvent.setup() };
};

// jsdom has no PointerEvent, so fireEvent.pointerDown drops the button. A MouseEvent keeps it.
const pointerDown = (target: Element, button: number) =>
    fireEvent(target, new MouseEvent('pointerdown', { bubbles: true, button }));

// jsdom has no layout, so the card stays hidden. Hidden options have no accessible name.
const rowTexts = () =>
    screen.getAllByRole('option', { hidden: true }).map((row) => row.textContent?.trim());

describe('PendingBoxCard', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        useRecentClasses().addRecentClass('col-1', 'deer');
    });

    afterEach(() => {
        usePendingBoxClass().cancel();
        vi.clearAllMocks();
    });

    it('focuses the class search with recent classes first', () => {
        setup();

        expect(screen.getByPlaceholderText('Pick a class')).toHaveFocus();
        expect(rowTexts()).toEqual(['deer', 'bobcat', 'coyote']);
    });

    it('picks the typed class', async () => {
        const { result, user } = setup();

        await user.keyboard('deer{Enter}');

        expect(pickClass).toHaveBeenCalledWith('col-1', 'deer');
        await expect(result).resolves.toBe('deer');
    });

    it('drops the box on Esc', async () => {
        const { result, user } = setup();

        await user.keyboard('{Escape}');

        await expect(result).resolves.toBeNull();
        expect(pickClass).not.toHaveBeenCalled();
    });

    it('drops the box on a click outside the card', async () => {
        const { result } = setup();

        await pointerDown(document.body, 0);

        await expect(result).resolves.toBeNull();
    });

    it('keeps the box on a right or middle click outside the card', async () => {
        setup();

        await pointerDown(document.body, 2);
        await pointerDown(document.body, 1);

        expect(get(usePendingBoxClass().request)).not.toBeNull();
    });

    it('keeps the box while panning with Space', async () => {
        setup('drag');

        await pointerDown(document.body, 0);

        expect(get(usePendingBoxClass().request)).not.toBeNull();
    });

    it('drops the box on Esc when the search has no focus, before other listeners see it', async () => {
        const windowListener = vi.fn();
        window.addEventListener('keydown', windowListener);
        const { result } = setup();
        screen.getByPlaceholderText('Pick a class').blur();

        await fireEvent.keyDown(document.body, { key: 'Escape' });
        window.removeEventListener('keydown', windowListener);

        await expect(result).resolves.toBeNull();
        expect(windowListener).not.toHaveBeenCalled();
    });

    it('keeps the box on a click inside the card', async () => {
        setup();

        await pointerDown(screen.getByPlaceholderText('Pick a class'), 0);

        expect(get(usePendingBoxClass().request)).not.toBeNull();
    });

    it('drops the box on the close button', async () => {
        const { result } = setup();

        await fireEvent.click(screen.getByLabelText('Close'));

        await expect(result).resolves.toBeNull();
        expect(pickClass).not.toHaveBeenCalled();
    });
});
