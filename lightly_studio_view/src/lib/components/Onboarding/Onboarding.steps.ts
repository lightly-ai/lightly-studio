import type { Driver, PopoverDOM } from 'driver.js';

type TourStage = 'grid' | 'menu' | 'tag_assign' | 'tile' | 'detail' | 'edit_button' | 'embedding';

interface StepPlan {
    count: number;
    indices: Partial<Record<TourStage, number>>;
}

/** Mutable shared state passed by reference between the component and the step functions. */
export interface TourRef {
    tour: Driver | undefined;
    stage: TourStage | null;
    menuHighlightCleanup: (() => void) | null;
    stepPlan: StepPlan;
}

interface StepsOptions {
    ref: TourRef;
    eligible: () => boolean;
    tile: () => Element | null;
    isSampleDetails: () => boolean;
    onSkip: () => void;
    onFinish: () => void;
    /** Calls `onboarding.start()` — transitions state to 'running' on the detail step. */
    onStartOnboarding: () => void;
    /** Calls `onboarding.dispatchOpenFirstSample()` from the driver.js "Open sample" button. */
    onOpenFirstSample: () => void;
}

/** Initial step plan used before the tour starts; recomputed at each tour start via buildStepPlan(). */
export const DEFAULT_STEP_PLAN: StepPlan = {
    count: 5,
    indices: { grid: 1, tag_assign: 2, menu: 3, tile: 4, detail: 5 }
};

export function visible(selector: string): Element | null {
    const element = document.querySelector(selector);
    return element?.getClientRects().length ? element : null;
}

export function tileElement(): Element | null {
    return visible('[data-testid="images-grid"] [data-testid="sample-grid-item"]');
}

/**
 * Computes which optional steps are present and returns the step count and per-stage index.
 * Called once at tour start so the dot indicators reflect the actual visible steps.
 */
export function buildStepPlan(): StepPlan {
    const hasEditButton = !!visible('[data-testid="header-editing-mode-button"]');
    const hasEmbedding = !!visible('[data-testid="side-panel-tabs-embed"]');

    const stages: TourStage[] = [
        'grid',
        'tag_assign',
        'menu',
        ...(hasEditButton ? (['edit_button'] as TourStage[]) : []),
        ...(hasEmbedding ? (['embedding'] as TourStage[]) : []),
        'tile',
        'detail'
    ];

    const indices: Partial<Record<TourStage, number>> = {};
    stages.forEach((stage, i) => {
        indices[stage] = i + 1;
    });

    return { count: stages.length, indices };
}

function openMenuDropdown(el: HTMLElement) {
    el.dispatchEvent(
        new PointerEvent('pointerdown', {
            bubbles: true,
            cancelable: true,
            isPrimary: true,
            button: 0,
            pointerType: 'mouse'
        })
    );
}

export function createTourSteps(opts: StepsOptions) {
    const { ref, eligible, tile, isSampleDetails, onSkip, onFinish, onStartOnboarding, onOpenFirstSample } =
        opts;

    function popoverFooter(stage: TourStage, skipFn: (() => void) | null) {
        return ({ footerButtons }: Pick<PopoverDOM, 'footerButtons'>) => {
            const stepIndex = ref.stepPlan.indices[stage] ?? 1;
            const stepCount = ref.stepPlan.count;
            const dots = document.createElement('div');
            dots.className = 'driver-tour-dots';
            for (let i = 1; i <= stepCount; i++) {
                const dot = document.createElement('span');
                dot.className = `driver-tour-dot${i === stepIndex ? ' driver-tour-dot--active' : ''}`;
                dots.appendChild(dot);
            }
            footerButtons.before(dots);

            if (skipFn) {
                const skip = document.createElement('button');
                skip.type = 'button';
                skip.textContent = 'Skip tour';
                skip.className = 'driver-popover-footer-btn driver-tour-skip-btn';
                skip.addEventListener('click', skipFn);
                footerButtons.before(skip);
            }
        };
    }

    function cleanupMenuHighlight() {
        ref.menuHighlightCleanup?.();
        ref.menuHighlightCleanup = null;
    }

    function highlightGrid() {
        if (!ref.tour || !eligible()) return;
        ref.stepPlan = buildStepPlan();
        ref.stage = 'grid';
        ref.tour.highlight({
            element: '[data-testid="images-grid"]',
            popover: {
                title: 'Browse your collection',
                description:
                    'Find what you need here. Filter by tag or search in the left panel to narrow down the images.',
                showButtons: ['next'],
                nextBtnText: 'Next',
                onNextClick: highlightTagAssign,
                onPopoverRender: popoverFooter('grid', onSkip)
            }
        });
    }

    function highlightTagAssign() {
        const tagAssign = visible('[data-onboarding-tag-assign]');
        if (!ref.tour || !tagAssign) return highlightMenuContent();
        ref.stage = 'tag_assign';
        ref.tour.highlight({
            element: tagAssign,
            popover: {
                title: 'Tag your images',
                description:
                    'Click any image to select it, then type a tag name here and press Enter to tag your selection.',
                showButtons: ['previous', 'next'],
                nextBtnText: 'Next',
                prevBtnText: 'Prev',
                onNextClick: highlightMenuContent,
                onPrevClick: highlightGrid,
                onPopoverRender: popoverFooter('tag_assign', onSkip)
            }
        });
    }

    function highlightMenuContent() {
        const menuButton = visible('[data-testid="menu-trigger"]');
        if (!ref.tour || !menuButton) return highlightEditButton();
        ref.stage = 'menu';

        openMenuDropdown(menuButton as HTMLElement);

        const observer = new MutationObserver(() => {
            if (!ref.tour || ref.stage !== 'menu') {
                observer.disconnect();
                return;
            }

            const content = visible('[data-select-content]');
            if (!content) return;

            observer.disconnect();

            // Lift the portal above driver.js's overlay (z-index 10000)
            const zStyle = document.createElement('style');
            zStyle.textContent = '[data-select-content]{z-index:10001!important;}';
            document.head.appendChild(zStyle);

            ref.menuHighlightCleanup = () => zStyle.remove();

            ref.tour?.highlight({
                element: content,
                popover: {
                    title: 'Run actions on your data',
                    description:
                        'Sample a representative subset, export your data, or split the dataset - all from this menu.',
                    showButtons: ['previous', 'next'],
                    nextBtnText: 'Next',
                    prevBtnText: 'Prev',
                    onNextClick: () => {
                        cleanupMenuHighlight();
                        // Transition driver.js to the new element BEFORE removing the
                        // portal from the DOM — prevents onDestroyed firing mid-tour.
                        highlightEditButton();
                        openMenuDropdown(menuButton as HTMLElement);
                    },
                    onPrevClick: () => {
                        cleanupMenuHighlight();
                        highlightTagAssign();
                        openMenuDropdown(menuButton as HTMLElement);
                    },
                    onPopoverRender: popoverFooter('menu', onSkip)
                }
            });
        });

        ref.menuHighlightCleanup = () => observer.disconnect();
        observer.observe(document.body, { childList: true, subtree: true });
    }

    function highlightEditButton() {
        const editButton = visible('[data-testid="header-editing-mode-button"]');
        if (!ref.tour || !editButton) return highlightEmbedding();
        ref.stage = 'edit_button';
        ref.tour.highlight({
            element: editButton,
            popover: {
                title: 'Edit annotations',
                description:
                    'Click Edit annotations to enter edit mode. From there you can draw bounding boxes, paint segmentation masks, and modify existing annotations directly on your images.',
                showButtons: ['previous', 'next'],
                nextBtnText: 'Next',
                prevBtnText: 'Prev',
                onNextClick: highlightEmbedding,
                onPrevClick: highlightMenuContent,
                onPopoverRender: popoverFooter('edit_button', onSkip)
            }
        });
    }

    function highlightEmbedding() {
        const embedButton = visible('[data-testid="side-panel-tabs-embed"]');
        if (!ref.tour || !embedButton) return highlightTile();
        ref.stage = 'embedding';
        ref.tour.highlight({
            element: embedButton,
            popover: {
                title: 'Explore the embedding space',
                description:
                    'Click the Embed icon to open an interactive scatter plot. See how your images relate to each other and filter your dataset by similarity.',
                showButtons: ['previous', 'next'],
                nextBtnText: 'Next',
                prevBtnText: 'Prev',
                onNextClick: highlightTile,
                onPrevClick: () => {
                    const editButton = visible('[data-testid="header-editing-mode-button"]');
                    if (editButton) highlightEditButton();
                    else highlightMenuContent();
                },
                onPopoverRender: popoverFooter('embedding', onSkip)
            }
        });
    }

    function highlightTile() {
        const target = tile();
        if (!ref.tour || !target) return;
        ref.stage = 'tile';
        ref.tour.highlight({
            element: target,
            popover: {
                title: 'Open an image',
                description:
                    'Single-click to select for tagging, double-click to open and inspect in detail.',
                showButtons: ['previous'],
                prevBtnText: 'Prev',
                onPrevClick: () => {
                    const embedButton = visible('[data-testid="side-panel-tabs-embed"]');
                    if (embedButton) return highlightEmbedding();
                    const editButton = visible('[data-testid="header-editing-mode-button"]');
                    if (editButton) return highlightEditButton();
                    highlightMenuContent();
                },
                onPopoverRender: (popover) => {
                    popoverFooter('tile', onSkip)(popover);
                    const openBtn = document.createElement('button');
                    openBtn.type = 'button';
                    openBtn.textContent = 'Open sample';
                    openBtn.className = 'driver-tour-open-btn driver-popover-footer-btn';
                    openBtn.addEventListener('click', onOpenFirstSample);
                    popover.footerButtons.appendChild(openBtn);
                }
            }
        });
    }

    function highlightDetail() {
        if (!ref.tour || !isSampleDetails() || !visible('[data-onboarding-detail]')) return;
        onStartOnboarding();
        ref.stage = 'detail';
        ref.tour.highlight({
            element: '[data-onboarding-detail]',
            popover: {
                title: 'Inspect and annotate',
                description:
                    'Explore the image, its annotations, and metadata. Use the arrows to walk through your collection one by one.',
                showButtons: ['next'],
                doneBtnText: 'Done',
                nextBtnText: 'Done',
                onNextClick: onFinish,
                onPopoverRender: popoverFooter('detail', null)
            }
        });
    }

    return {
        highlightGrid,
        highlightTagAssign,
        highlightMenuContent,
        highlightEditButton,
        highlightEmbedding,
        highlightTile,
        highlightDetail,
        cleanupMenuHighlight
    };
}
