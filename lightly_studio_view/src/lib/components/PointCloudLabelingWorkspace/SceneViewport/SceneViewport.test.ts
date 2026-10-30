import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { readonly, writable } from 'svelte/store';
import SceneViewport from './SceneViewport.svelte';
import SceneViewportGroupHarness from './SceneViewportGroupHarness.svelte';

const transforms = {
    annotations: readonly(writable([])),
    reconcile: vi.fn(),
    begin: vi.fn(),
    cancel: vi.fn(),
    commit: vi.fn()
};

vi.mock('@threlte/core', () => ({ Canvas: () => {} }));
vi.mock('$lib/components/PointCloudViewer', () => ({ PointCloudScene: () => {} }));
vi.mock('./RotationCursor/RotationCursor.svelte', () => ({ default: () => {} }));
vi.mock('./SceneNavigationControls.svelte', () => ({ default: () => {} }));
vi.mock('$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidLayer.svelte', () => ({
    default: () => {}
}));
vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidTooltip/CuboidTooltipOverlay.svelte',
    () => ({ default: () => {} })
);
vi.mock('$lib/components/PointCloudLabelingWorkspace/GroundPlane/GroundPlane.svelte', () => ({
    default: () => {}
}));
vi.mock('$lib/components/PointCloudLabelingWorkspace/OriginAxes/OriginAxes.svelte', () => ({
    default: () => {}
}));

function press(target: Element | Window, key: string, init: KeyboardEventInit = {}) {
    const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
    target.dispatchEvent(event);
    return event;
}

describe('SceneViewport arrow-key navigation', () => {
    const onPreviousTick = vi.fn();
    const onNextTick = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        const { getByTestId } = render(SceneViewport, {
            props: { transforms, onPreviousTick, onNextTick }
        });
        fireEvent.pointerEnter(getByTestId('workspace-scene-viewport'));
    });

    it('calls the previous and next handlers and prevents the default action', () => {
        expect(press(window, 'ArrowLeft').defaultPrevented).toBe(true);
        expect(onPreviousTick).toHaveBeenCalledOnce();

        expect(press(window, 'ArrowRight').defaultPrevented).toBe(true);
        expect(onNextTick).toHaveBeenCalledOnce();
    });

    it('ignores other keys and modified arrow keys', () => {
        expect(press(window, 'ArrowUp').defaultPrevented).toBe(false);
        for (const modifier of ['altKey', 'ctrlKey', 'metaKey', 'shiftKey']) {
            expect(press(window, 'ArrowLeft', { [modifier]: true }).defaultPrevented).toBe(false);
        }
        expect(onPreviousTick).not.toHaveBeenCalled();
        expect(onNextTick).not.toHaveBeenCalled();
    });

    it.each([
        ['input', '<input />'],
        ['textarea', '<textarea></textarea>'],
        ['select', '<select></select>'],
        ['slider', '<div role="slider"></div>'],
        ['contenteditable="true"', '<div contenteditable="true"></div>'],
        ['contenteditable=""', '<div contenteditable=""></div>'],
        ['contenteditable="plaintext-only"', '<div contenteditable="plaintext-only"></div>'],
        ['editable ancestor', '<div contenteditable=""><span></span></div>']
    ])('leaves arrow keys to %s', (_name, html) => {
        const container = document.createElement('div');
        container.innerHTML = html;
        document.body.appendChild(container);
        const target = container.querySelector('span') ?? container.firstElementChild!;

        expect(press(target, 'ArrowLeft').defaultPrevented).toBe(false);
        expect(onPreviousTick).not.toHaveBeenCalled();
        container.remove();
    });

    it('still handles keys from a contenteditable="false" element', () => {
        const element = document.createElement('div');
        element.setAttribute('contenteditable', 'false');
        document.body.appendChild(element);

        expect(press(element, 'ArrowRight').defaultPrevented).toBe(true);
        expect(onNextTick).toHaveBeenCalledOnce();
        element.remove();
    });
});

it('transfers navigation exclusively between the hovered and focused viewports', async () => {
    const onMainNext = vi.fn();
    const onTopNext = vi.fn();
    const { getAllByTestId, getByRole } = render(SceneViewportGroupHarness, {
        props: { transforms, onMainNext, onTopNext }
    });
    const [main, top] = getAllByTestId('workspace-scene-viewport');
    await fireEvent.pointerEnter(main);
    await fireEvent.pointerEnter(top);
    expect(main.getAttribute('aria-current')).toBeNull();
    expect(top.getAttribute('aria-current')).toBe('true');
    press(window, 'ArrowRight');
    expect(onTopNext).toHaveBeenCalledOnce();
    expect(onMainNext).not.toHaveBeenCalled();
    await fireEvent.focusIn(getByRole('button', { name: 'Scene settings' }));
    expect(top.getAttribute('aria-current')).toBeNull();
    press(window, 'ArrowRight');
    expect(onMainNext).toHaveBeenCalledOnce();
    expect(onTopNext).toHaveBeenCalledOnce();
});
