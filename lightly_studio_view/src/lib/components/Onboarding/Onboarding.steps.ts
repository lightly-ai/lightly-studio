import type { Driver, PopoverDOM } from 'driver.js';

type TourStage = 'grid' | 'menu' | 'tag_assign' | 'tile' | 'detail';

/** Mutable shared state passed by reference between the component and the step functions. */
export interface TourRef {
    tour: Driver | undefined;
    stage: TourStage | null;
    menuHighlightCleanup: (() => void) | null;
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

export const STEP_COUNT = 5;

export function visible(selector: string): Element | null {
    const element = document.querySelector(selector);
    return element?.getClientRects().length ? element : null;
}

export function tileElement(): Element | null {
    return visible('[data-testid="images-grid"] [data-testid="sample-grid-item"]');
}

function popoverFooter(stepIndex: number, skipFn: (() => void) | null) {
    return ({ footerButtons }: Pick<PopoverDOM, 'footerButtons'>) => {
        const dots = document.createElement('div');
        dots.className = 'driver-tour-dots';
        for (let i = 1; i <= STEP_COUNT; i++) {
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

    function cleanupMenuHighlight() {
        ref.menuHighlightCleanup?.();
        ref.menuHighlightCleanup = null;
    }

    function highlightGrid() {
        if (!ref.tour || !eligible()) return;
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
                onPopoverRender: popoverFooter(1, onSkip)
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
                onPopoverRender: popoverFooter(2, onSkip)
            }
        });
    }

    function highlightMenuContent() {
        const menuButton = visible('[data-testid="menu-trigger"]');
        if (!ref.tour || !menuButton) return highlightTile();
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
                        highlightTile();
                        openMenuDropdown(menuButton as HTMLElement);
                    },
                    onPrevClick: () => {
                        cleanupMenuHighlight();
                        highlightTagAssign();
                        openMenuDropdown(menuButton as HTMLElement);
                    },
                    onPopoverRender: popoverFooter(3, onSkip)
                }
            });
        });

        ref.menuHighlightCleanup = () => observer.disconnect();
        observer.observe(document.body, { childList: true, subtree: true });
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
                onPrevClick: highlightMenuContent,
                onPopoverRender: (popover) => {
                    popoverFooter(4, onSkip)(popover);
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
                onPopoverRender: popoverFooter(5, null)
            }
        });
    }

    return {
        highlightGrid,
        highlightTagAssign,
        highlightMenuContent,
        highlightTile,
        highlightDetail,
        cleanupMenuHighlight
    };
}
