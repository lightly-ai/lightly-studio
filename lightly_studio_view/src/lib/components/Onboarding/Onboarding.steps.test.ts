import { describe, it, expect, vi, beforeEach } from 'vitest';
import { buildStepPlan, createTourSteps, DEFAULT_STEP_PLAN } from './Onboarding.steps';
import type { TourRef } from './Onboarding.steps';

function makeElement(visible = true): Element {
    return {
        getClientRects: () => (visible ? [{}] : [])
    } as unknown as Element;
}

function mockQuerySelector(map: Record<string, boolean>) {
    vi.spyOn(document, 'querySelector').mockImplementation((selector: string) => {
        const key = Object.keys(map).find((k) => selector.includes(k));
        if (key === undefined || !map[key]) return null;
        return makeElement(true);
    });
}

beforeEach(() => {
    vi.restoreAllMocks();
});

describe('buildStepPlan', () => {
    it('returns 5 steps when neither optional step is visible and panel is open', () => {
        mockQuerySelector({ 'header-editing-mode-button': false, 'side-panel-tabs-embed': false });

        const plan = buildStepPlan(false);

        expect(plan.count).toBe(5);
        expect(plan.indices).toMatchObject({ grid: 1, tag_assign: 2, menu: 3, tile: 4, detail: 5 });
        expect(plan.indices.edit_button).toBeUndefined();
        expect(plan.indices.embedding).toBeUndefined();
        expect(plan.indices.open_filter_panel).toBeUndefined();
    });

    it('returns 6 steps when panel is collapsed and no other optional steps are visible', () => {
        mockQuerySelector({ 'header-editing-mode-button': false, 'side-panel-tabs-embed': false });

        const plan = buildStepPlan(true);

        expect(plan.count).toBe(6);
        expect(plan.indices).toMatchObject({
            grid: 1,
            open_filter_panel: 2,
            tag_assign: 3,
            menu: 4,
            tile: 5,
            detail: 6
        });
        expect(plan.indices.edit_button).toBeUndefined();
        expect(plan.indices.embedding).toBeUndefined();
    });

    it('returns 6 steps when only the edit button is visible', () => {
        mockQuerySelector({ 'header-editing-mode-button': true, 'side-panel-tabs-embed': false });

        const plan = buildStepPlan(false);

        expect(plan.count).toBe(6);
        expect(plan.indices).toMatchObject({
            grid: 1,
            tag_assign: 2,
            menu: 3,
            edit_button: 4,
            tile: 5,
            detail: 6
        });
        expect(plan.indices.embedding).toBeUndefined();
    });

    it('returns 6 steps when only the embed button is visible', () => {
        mockQuerySelector({ 'header-editing-mode-button': false, 'side-panel-tabs-embed': true });

        const plan = buildStepPlan(false);

        expect(plan.count).toBe(6);
        expect(plan.indices).toMatchObject({
            grid: 1,
            tag_assign: 2,
            menu: 3,
            embedding: 4,
            tile: 5,
            detail: 6
        });
        expect(plan.indices.edit_button).toBeUndefined();
    });

    it('returns 7 steps when both optional steps are visible', () => {
        mockQuerySelector({ 'header-editing-mode-button': true, 'side-panel-tabs-embed': true });

        const plan = buildStepPlan(false);

        expect(plan.count).toBe(7);
        expect(plan.indices).toMatchObject({
            grid: 1,
            tag_assign: 2,
            menu: 3,
            edit_button: 4,
            embedding: 5,
            tile: 6,
            detail: 7
        });
    });
});

describe('DEFAULT_STEP_PLAN', () => {
    it('has 5 steps with base indices', () => {
        expect(DEFAULT_STEP_PLAN.count).toBe(5);
        expect(DEFAULT_STEP_PLAN.indices).toMatchObject({
            grid: 1,
            tag_assign: 2,
            menu: 3,
            tile: 4,
            detail: 5
        });
    });
});

// Helpers to build a minimal TourRef and a highlight spy for navigation tests.
function makeRef(): TourRef {
    return {
        tour: undefined,
        stage: null,
        menuHighlightCleanup: null,
        stepPlan: { ...DEFAULT_STEP_PLAN }
    };
}

function makeHighlightSpy() {
    return vi.fn();
}

function mockRequestAnimationFrame() {
    let callback: FrameRequestCallback;
    vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation((nextFrame) => {
        callback = nextFrame;
        return 0;
    });
    return () => callback(0);
}

function makeOpts(ref: TourRef, overrides: Partial<Parameters<typeof createTourSteps>[0]> = {}) {
    return createTourSteps({
        ref,
        eligible: () => true,
        tile: () => makeElement(true),
        isSampleDetails: () => false,
        onSkip: vi.fn(),
        onFinish: vi.fn(),
        onStartOnboarding: vi.fn(),
        onOpenFirstSample: vi.fn(),
        openFilterPanel: vi.fn(),
        isFilterPanelCollapsed: () => false,
        ...overrides
    });
}

describe('highlightEditButton fallthrough', () => {
    it('falls through to highlightEmbedding when edit button is absent', () => {
        const ref = makeRef();
        const highlight = makeHighlightSpy();
        ref.tour = { highlight } as unknown as TourRef['tour'];

        // embed button is visible, edit button is not
        mockQuerySelector({ 'header-editing-mode-button': false, 'side-panel-tabs-embed': true });

        const steps = makeOpts(ref);
        steps.highlightEditButton();

        expect(ref.stage).toBe('embedding');
    });

    it('falls through to highlightTile when both optional steps are absent', () => {
        const ref = makeRef();
        const highlight = makeHighlightSpy();
        ref.tour = { highlight } as unknown as TourRef['tour'];

        mockQuerySelector({ 'header-editing-mode-button': false, 'side-panel-tabs-embed': false });

        const steps = makeOpts(ref);
        steps.highlightEditButton();

        expect(ref.stage).toBe('tile');
    });

    it('shows the edit button step when the element is visible', () => {
        const ref = makeRef();
        const highlight = makeHighlightSpy();
        ref.tour = { highlight } as unknown as TourRef['tour'];

        mockQuerySelector({ 'header-editing-mode-button': true, 'side-panel-tabs-embed': false });

        const steps = makeOpts(ref);
        steps.highlightEditButton();

        expect(ref.stage).toBe('edit_button');
        expect(highlight).toHaveBeenCalledOnce();
    });
});

describe('highlightTile', () => {
    it('calls onSkip when tile target is missing', () => {
        const ref = makeRef();
        ref.tour = { highlight: vi.fn() } as unknown as TourRef['tour'];

        mockQuerySelector({});

        const onSkip = vi.fn();
        const steps = makeOpts(ref, { tile: () => null, onSkip });
        steps.highlightTile();

        expect(onSkip).toHaveBeenCalledOnce();
    });

    it('does not call onSkip when ref.tour is unavailable', () => {
        const onSkip = vi.fn();
        const ref = makeRef(); // ref.tour is undefined

        mockQuerySelector({});

        const steps = makeOpts(ref, { tile: () => null, onSkip });
        steps.highlightTile();

        expect(onSkip).not.toHaveBeenCalled();
    });
});

describe('highlightOpenFilterPanel', () => {
    it('calls openFilterPanel and sets stage to open_filter_panel after rAF', async () => {
        const ref = makeRef();
        const highlight = makeHighlightSpy();
        ref.tour = { highlight } as unknown as TourRef['tour'];

        mockQuerySelector({ 'images-grid': true });

        // Stub querySelector to return a visible element for data-onboarding-filter-panel
        const panelEl = makeElement(true);
        vi.spyOn(document, 'querySelector').mockImplementation((sel: string) => {
            if (sel === '[data-onboarding-filter-panel]') return panelEl;
            return null;
        });

        const openFilterPanel = vi.fn();
        const runAnimationFrame = mockRequestAnimationFrame();

        const steps = makeOpts(ref, { openFilterPanel, isFilterPanelCollapsed: () => true });
        steps.highlightOpenFilterPanel();

        expect(openFilterPanel).toHaveBeenCalledOnce();
        expect(highlight).not.toHaveBeenCalled();

        runAnimationFrame();

        expect(highlight).toHaveBeenCalledWith(
            expect.objectContaining({
                element: panelEl,
                popover: expect.objectContaining({ title: 'Filter panel' })
            })
        );
    });

    it('does nothing when ref.tour is unavailable', () => {
        const ref = makeRef(); // ref.tour is undefined
        const openFilterPanel = vi.fn();

        const steps = makeOpts(ref, { openFilterPanel });
        steps.highlightOpenFilterPanel();

        expect(openFilterPanel).not.toHaveBeenCalled();
    });

    it('skips highlight when panel element is missing after rAF', () => {
        const ref = makeRef();
        const highlight = makeHighlightSpy();
        ref.tour = { highlight } as unknown as TourRef['tour'];

        vi.spyOn(document, 'querySelector').mockReturnValue(null);

        const runAnimationFrame = mockRequestAnimationFrame();

        const steps = makeOpts(ref);
        steps.highlightOpenFilterPanel();
        runAnimationFrame();

        expect(highlight).not.toHaveBeenCalled();
    });
});

describe('highlightEmbedding fallthrough', () => {
    it('falls through to highlightTile when embed button is absent', () => {
        const ref = makeRef();
        const highlight = makeHighlightSpy();
        ref.tour = { highlight } as unknown as TourRef['tour'];

        mockQuerySelector({ 'side-panel-tabs-embed': false, 'header-editing-mode-button': false });

        const steps = makeOpts(ref);
        steps.highlightEmbedding();

        expect(ref.stage).toBe('tile');
    });

    it('shows the embedding step when the element is visible', () => {
        const ref = makeRef();
        const highlight = makeHighlightSpy();
        ref.tour = { highlight } as unknown as TourRef['tour'];

        mockQuerySelector({ 'side-panel-tabs-embed': true, 'header-editing-mode-button': false });

        const steps = makeOpts(ref);
        steps.highlightEmbedding();

        expect(ref.stage).toBe('embedding');
        expect(highlight).toHaveBeenCalledOnce();
    });
});
