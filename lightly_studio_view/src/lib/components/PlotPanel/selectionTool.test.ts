import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    SELECTION_TOOLS,
    createSelectionToolController,
    findToolButtons,
    isButtonArmed,
    toolButtonToToggle,
    type ToolMode
} from './selectionTool';

const ARMED_STYLE = 'background: color-mix(in srgb, red 50%, transparent)';
const RECT_TITLE = 'Toggle rectangle selection mode. In normal mode, use shift + drag.';
const LASSO_TITLE = 'Toggle lasso selection mode. In normal mode, use shift + meta + drag.';

function buildContainer(options: { armed?: 'marquee' | 'lasso'; titled?: boolean } = {}) {
    const { armed, titled = true } = options;
    const container = document.createElement('div');
    const view = document.createElement('div');
    view.className = 'embedding-view';
    const marquee = document.createElement('button');
    const lasso = document.createElement('button');
    if (titled) {
        marquee.setAttribute('title', RECT_TITLE);
        lasso.setAttribute('title', LASSO_TITLE);
    }
    if (armed === 'marquee') marquee.setAttribute('style', ARMED_STYLE);
    if (armed === 'lasso') lasso.setAttribute('style', ARMED_STYLE);
    view.append(marquee, lasso);
    container.append(view);
    document.body.append(container);
    return { container, marquee, lasso };
}

// jsdom fires MutationObserver callbacks on the microtask queue; awaiting a macrotask
// guarantees they have run.
const flushObservers = () => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
    document.body.innerHTML = '';
    vi.useRealTimers();
});

describe('SELECTION_TOOLS', () => {
    it('lists pan, rectangle and lasso in order', () => {
        expect(SELECTION_TOOLS.map((tool) => tool.mode)).toEqual(['pan', 'rectangle', 'lasso']);
        expect(SELECTION_TOOLS.every((tool) => tool.label.length > 0)).toBe(true);
    });
});

describe('isButtonArmed', () => {
    it('detects the library color-mix marker', () => {
        const button = document.createElement('button');
        expect(isButtonArmed(button)).toBe(false);
        button.setAttribute('style', ARMED_STYLE);
        expect(isButtonArmed(button)).toBe(true);
    });

    it('treats a missing button as unarmed', () => {
        expect(isButtonArmed(null)).toBe(false);
    });
});

describe('findToolButtons', () => {
    it('resolves buttons by their title text', () => {
        const { container, marquee, lasso } = buildContainer();
        expect(findToolButtons(container)).toEqual({ marquee, lasso });
    });

    it('falls back to DOM order when titles are missing', () => {
        const { container, marquee, lasso } = buildContainer({ titled: false });
        expect(findToolButtons(container)).toEqual({ marquee, lasso });
    });

    it('fills only the missing side when one title changes', () => {
        const { container, marquee, lasso } = buildContainer();
        lasso.removeAttribute('title');
        expect(findToolButtons(container)).toEqual({ marquee, lasso });
    });

    it('returns nulls for a missing container', () => {
        expect(findToolButtons(undefined)).toEqual({ marquee: null, lasso: null });
    });
});

describe('toolButtonToToggle', () => {
    it('arms the marquee for rectangle when it is off', () => {
        const { container, marquee } = buildContainer();
        expect(toolButtonToToggle(container, 'rectangle')).toBe(marquee);
    });

    it('leaves an already-armed tool alone', () => {
        const { container } = buildContainer({ armed: 'lasso' });
        expect(toolButtonToToggle(container, 'lasso')).toBeNull();
    });

    it('disarms the armed tool when switching to pan', () => {
        const { container, marquee } = buildContainer({ armed: 'marquee' });
        expect(toolButtonToToggle(container, 'pan')).toBe(marquee);
    });

    it('does nothing for pan when no tool is armed', () => {
        const { container } = buildContainer();
        expect(toolButtonToToggle(container, 'pan')).toBeNull();
    });
});

describe('createSelectionToolController', () => {
    let activeTool: ToolMode;

    beforeEach(() => {
        activeTool = 'pan';
    });

    it('does not click anything when pan is active and no tool is armed', () => {
        const { container, marquee, lasso } = buildContainer();
        const marqueeClick = vi.spyOn(marquee, 'click');
        const lassoClick = vi.spyOn(lasso, 'click');
        const controller = createSelectionToolController(container, () => activeTool);
        expect(marqueeClick).not.toHaveBeenCalled();
        expect(lassoClick).not.toHaveBeenCalled();
        controller.destroy();
    });

    it('clicks the target button on reconcile and guards against re-entrant clicks', () => {
        const { container, lasso } = buildContainer();
        const lassoClick = vi.spyOn(lasso, 'click');
        const controller = createSelectionToolController(container, () => activeTool);

        activeTool = 'lasso';
        controller.reconcile();
        controller.reconcile();

        // The guard holds until the style observer confirms the change.
        expect(lassoClick).toHaveBeenCalledTimes(1);
        controller.destroy();
    });

    it('re-arms the tool after the library resets it (sticky)', async () => {
        const { container, lasso } = buildContainer({ armed: 'lasso' });
        activeTool = 'lasso';
        const lassoClick = vi.spyOn(lasso, 'click');
        const controller = createSelectionToolController(container, () => activeTool);

        // Already armed: nothing to do yet.
        expect(lassoClick).not.toHaveBeenCalled();

        // The library commits a selection and drops back to "none".
        lasso.removeAttribute('style');
        await flushObservers();

        expect(lassoClick).toHaveBeenCalledTimes(1);
        controller.destroy();
    });

    it('clears the guard once the safety timeout elapses', () => {
        vi.useFakeTimers();
        const { container, lasso } = buildContainer();
        const lassoClick = vi.spyOn(lasso, 'click');
        const controller = createSelectionToolController(container, () => activeTool);

        activeTool = 'lasso';
        controller.reconcile();
        expect(lassoClick).toHaveBeenCalledTimes(1);

        vi.advanceTimersByTime(250);
        // Guard released, and the tool is still unarmed, so the next reconcile clicks again.
        controller.reconcile();
        expect(lassoClick).toHaveBeenCalledTimes(2);
        controller.destroy();
    });

    it('stops reacting to mutations after destroy', async () => {
        const { container, lasso } = buildContainer({ armed: 'lasso' });
        activeTool = 'lasso';
        const lassoClick = vi.spyOn(lasso, 'click');
        const controller = createSelectionToolController(container, () => activeTool);
        controller.destroy();

        lasso.removeAttribute('style');
        await flushObservers();

        expect(lassoClick).not.toHaveBeenCalled();
    });
});
