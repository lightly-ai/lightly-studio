import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import AnnotationCardFrame from './AnnotationCardFrame.svelte';
import { fakeLayer } from './fakeLayer.testFixtures';

const renderFrame = (
    context: Record<string, unknown>,
    layer = fakeLayer().layer,
    props: Record<string, unknown> = {}
) =>
    render(AnnotationCardFrame, {
        props: {
            bbox: { x: 100, y: 100, width: 50, height: 50 },
            getLayer: () => layer,
            label: 'Annotation bobcat',
            testId: 'frame',
            children: createRawSnippet(() => ({ render: () => '<span>body</span>' })),
            ...props
        },
        context: new Map<string, unknown>([['annotation-label', context]])
    });

describe('AnnotationCardFrame', () => {
    it('shows once it has found its place, as a named group', async () => {
        renderFrame({});

        await waitFor(() =>
            expect(screen.getByRole('group', { name: 'Annotation bobcat' })).toBeVisible()
        );
    });

    it.each(['isDrawing', 'isMovingAnnotation'])('hides while %s is set', async (flag) => {
        const context = $state<Record<string, unknown>>({});
        renderFrame(context);
        await waitFor(() => expect(screen.getByTestId('frame')).toBeVisible());

        context[flag] = true;

        await waitFor(() => expect(screen.getByTestId('frame')).not.toBeVisible());
        expect(screen.getByText('body')).toBeInTheDocument();
    });

    it('follows the box when the canvas pans or zooms', async () => {
        const { layer, setMatrix } = fakeLayer();
        renderFrame({}, layer);
        await waitFor(() => expect(screen.getByTestId('frame')).toHaveStyle({ left: '158px' }));

        setMatrix({ a: 2, d: 2, e: 10, f: 20 });

        await waitFor(() => expect(screen.getByTestId('frame')).toHaveStyle({ left: '318px' }));
        expect(screen.getByTestId('frame')).toHaveStyle({ top: '220px' });
    });

    it('hides while the box is panned off the canvas', async () => {
        const { layer, setMatrix } = fakeLayer();
        renderFrame({}, layer);
        await waitFor(() => expect(screen.getByTestId('frame')).toBeVisible());

        setMatrix({ a: 1, d: 1, e: 2000, f: 0 });

        await waitFor(() => expect(screen.getByTestId('frame')).not.toBeVisible());
    });

    it('hides when its layer goes away', async () => {
        let layer = $state<SVGGraphicsElement | null>(fakeLayer().layer);
        renderFrame({}, undefined, { getLayer: () => layer });
        await waitFor(() => expect(screen.getByTestId('frame')).toBeVisible());

        layer = null;

        await waitFor(() => expect(screen.getByTestId('frame')).not.toBeVisible());
    });

    it('reports a pointer press outside the card only', async () => {
        const onPointerDownOutside = vi.fn();
        renderFrame({}, undefined, { onPointerDownOutside });
        await waitFor(() => expect(screen.getByTestId('frame')).toBeVisible());

        await fireEvent.pointerDown(screen.getByText('body'));
        expect(onPointerDownOutside).not.toHaveBeenCalled();
        await fireEvent.pointerDown(document.body);
        expect(onPointerDownOutside).toHaveBeenCalledOnce();
    });

    it('ignores a pointer press while hidden, like the click that brings the box back', async () => {
        const onPointerDownOutside = vi.fn();
        const { layer, setMatrix } = fakeLayer();
        renderFrame({}, layer, { onPointerDownOutside });
        setMatrix({ a: 1, d: 1, e: 2000, f: 0 });
        await waitFor(() => expect(screen.getByTestId('frame')).not.toBeVisible());

        await fireEvent.pointerDown(document.body);

        expect(onPointerDownOutside).not.toHaveBeenCalled();
    });
});
