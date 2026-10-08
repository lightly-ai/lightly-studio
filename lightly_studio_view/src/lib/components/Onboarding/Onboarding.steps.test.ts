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
    it('returns 5 steps when neither optional step is visible', () => {
        mockQuerySelector({ 'header-editing-mode-button': false, 'side-panel-tabs-embed': false });

        const plan = buildStepPlan();

        expect(plan.count).toBe(5);
        expect(plan.indices).toMatchObject({ grid: 1, tag_assign: 2, menu: 3, tile: 4, detail: 5 });
        expect(plan.indices.edit_button).toBeUndefined();
        expect(plan.indices.embedding).toBeUndefined();
    });

    it('returns 6 steps when only the edit button is visible', () => {
        mockQuerySelector({ 'header-editing-mode-button': true, 'side-panel-tabs-embed': false });

        const plan = buildStepPlan();

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

        const plan = buildStepPlan();

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

        const plan = buildStepPlan();

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
