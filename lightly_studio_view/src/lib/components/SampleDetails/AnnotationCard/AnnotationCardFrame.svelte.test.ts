import { render, screen, waitFor } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it } from 'vitest';
import AnnotationCardFrame from './AnnotationCardFrame.svelte';

// jsdom has no layout, so a fake layer gives the frame a screen matrix and a canvas to sit in.
const layer = {
    getScreenCTM: () => ({ a: 1, d: 1, e: 0, f: 0 }),
    ownerSVGElement: {
        getBoundingClientRect: () => ({ left: 0, top: 0, right: 800, bottom: 600 })
    }
} as unknown as SVGGraphicsElement;

const renderFrame = (context: Record<string, unknown>) =>
    render(AnnotationCardFrame, {
        props: {
            bbox: { x: 100, y: 100, width: 50, height: 50 },
            getLayer: () => layer,
            testId: 'frame',
            children: createRawSnippet(() => ({ render: () => '<span>body</span>' }))
        },
        context: new Map<string, unknown>([['annotation-label', context]])
    });

describe('AnnotationCardFrame', () => {
    it('shows once it has found its place', async () => {
        renderFrame({});

        await waitFor(() => expect(screen.getByTestId('frame')).toBeVisible());
    });

    it.each(['isDrawing', 'isMovingAnnotation'])('hides while %s is set', async (flag) => {
        const context = $state<Record<string, unknown>>({});
        renderFrame(context);
        await waitFor(() => expect(screen.getByTestId('frame')).toBeVisible());

        context[flag] = true;

        await waitFor(() => expect(screen.getByTestId('frame')).not.toBeVisible());
        expect(screen.getByText('body')).toBeInTheDocument();
    });
});
