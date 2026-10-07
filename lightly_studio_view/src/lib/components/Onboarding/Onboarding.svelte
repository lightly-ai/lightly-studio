<script lang="ts">
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import { usePostHog } from '$lib/hooks';
    import { TOUR_VERSION, useOnboarding } from '$lib/hooks/useOnboarding/useOnboarding';
    import { get } from 'svelte/store';
    import { onDestroy, onMount } from 'svelte';
    import type { Driver, PopoverDOM } from 'driver.js';
    import Invitation from './Invitation.svelte';

    interface Props {
        /** Whether the onboarding feature is enabled for the current user. */
        enabled: boolean;
        /** Whether the current route is the images grid view. */
        isImages: boolean;
        /** Whether the current route is the sample detail view. */
        isSampleDetails: boolean;
        /** ID of the active collection. */
        collectionId: string;
        /** Type of the active collection (e.g. `"tag"`, `"embedding"`). */
        collectionType: string;
        /** ID of the dataset that owns the collection. */
        datasetId: string;
        /** Number of samples in the collection; used to gate the tour invitation. */
        sampleCount: number;
        /**
         * Monotonically-incrementing counter. Incrementing it triggers a tour
         * replay without needing a separate callback prop.
         */
        replayRequest: number;
    }

    let {
        enabled,
        isImages,
        isSampleDetails,
        collectionId,
        collectionType,
        datasetId,
        sampleCount,
        replayRequest
    }: Props = $props();

    const onboarding = useOnboarding();
    const { state } = onboarding;
    const { ready, trackEvent } = usePostHog();
    const STEP_COUNT = 5;

    let tour: Driver | undefined;
    let menuHighlightCleanup: (() => void) | null = null;
    let stage: 'grid' | 'menu' | 'tag_assign' | 'tile' | 'detail' | null = null;
    let trackingReady = false;
    let checkingEligibility = false;
    let suppressDismiss = false;
    let replaySeen = 0;
    let loadingDetail = false;
    let activeCollectionId: string | null = null;

    function track(event: string, properties: Record<string, unknown> = {}) {
        if (!trackingReady) return;
        trackEvent(event, {
            tour_version: TOUR_VERSION,
            collection_id: collectionId,
            ...properties
        });
    }

    const skipTour = () => dismiss('skip_button');

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

    function visible(selector: string): Element | null {
        const element = document.querySelector(selector);
        return element?.getClientRects().length ? element : null;
    }

    function tile(): Element | null {
        return visible('[data-testid="images-grid"] [data-testid="sample-grid-item"]');
    }

    function eligible(): boolean {
        return enabled && isImages && sampleCount > 0 && !!tile();
    }

    async function offerInvitation() {
        if (checkingEligibility || get(state) !== 'unseen' || !eligible()) return;
        checkingEligibility = true;
        trackingReady = await ready;
        checkingEligibility = false;
        if (get(state) === 'unseen' && eligible() && onboarding.invite()) {
            track('onboarding_invitation_shown');
        }
    }

    function cleanupMenuHighlight() {
        menuHighlightCleanup?.();
        menuHighlightCleanup = null;
    }

    function dismiss(dismissalStage: string) {
        if (get(state) === 'finished' || get(state) === 'unseen') return;
        cleanupMenuHighlight();
        track('onboarding_dismissed', { dismissal_stage: dismissalStage });
        onboarding.dismiss();
        stage = null;
        tour?.destroy();
        tour = undefined;
    }

    function finish() {
        cleanupMenuHighlight();
        track('onboarding_completed');
        onboarding.complete();
        stage = null;
        tour?.destroy();
        tour = undefined;
    }

    function highlightGrid() {
        if (!tour || !eligible()) return;
        stage = 'grid';
        tour.highlight({
            element: '[data-testid="images-grid"]',
            popover: {
                title: 'Browse your collection',
                description:
                    'Find what you need here. Filter by tag or search in the left panel to narrow down the images.',
                showButtons: ['next'],
                nextBtnText: 'Next',
                onNextClick: highlightTagAssign,
                onPopoverRender: popoverFooter(1, skipTour)
            }
        });
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

    function highlightTagAssign() {
        const tagAssign = visible('[data-onboarding-tag-assign]');
        if (!tour || !tagAssign) return highlightMenuContent();
        stage = 'tag_assign';
        tour.highlight({
            element: tagAssign,
            popover: {
                title: 'Label your images',
                description:
                    'Click any image to select it, then type a tag name here and press Enter to label your selection.',
                showButtons: ['previous', 'next'],
                nextBtnText: 'Next',
                prevBtnText: 'Prev',
                onNextClick: highlightMenuContent,
                onPrevClick: highlightGrid,
                onPopoverRender: popoverFooter(2, skipTour)
            }
        });
    }

    function highlightMenuContent() {
        const menuButton = visible('[data-testid="menu-trigger"]');
        if (!tour || !menuButton) return highlightTile();
        stage = 'menu';

        openMenuDropdown(menuButton as HTMLElement);

        const observer = new MutationObserver(() => {
            if (!tour || stage !== 'menu') {
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

            menuHighlightCleanup = () => zStyle.remove();

            tour?.highlight({
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
                    onPopoverRender: popoverFooter(3, skipTour)
                }
            });
        });

        menuHighlightCleanup = () => observer.disconnect();
        observer.observe(document.body, { childList: true, subtree: true });
    }

    function highlightTile() {
        const target = tile();
        if (!tour || !target) return;
        stage = 'tile';
        tour.highlight({
            element: target,
            popover: {
                title: 'Open an image',
                description:
                    'Single-click to select for tagging, double-click to open and inspect in detail.',
                showButtons: ['previous'],
                prevBtnText: 'Prev',
                onPrevClick: highlightMenuContent,
                onPopoverRender: (popover) => {
                    popoverFooter(4, skipTour)(popover);
                    const openBtn = document.createElement('button');
                    openBtn.type = 'button';
                    openBtn.textContent = 'Open sample';
                    openBtn.className = 'driver-tour-open-btn driver-popover-footer-btn';
                    openBtn.addEventListener('click', () => {
                        window.dispatchEvent(new CustomEvent('onboarding:open-first-sample'));
                    });
                    popover.footerButtons.appendChild(openBtn);
                }
            }
        });
    }

    function highlightDetail() {
        if (!tour || !isSampleDetails || !visible('[data-onboarding-detail]')) return;
        onboarding.start();
        stage = 'detail';
        tour.highlight({
            element: '[data-onboarding-detail]',
            popover: {
                title: 'Inspect and annotate',
                description:
                    'Explore the image, its annotations, and metadata. Use the arrows to walk through your collection one by one.',
                showButtons: ['next'],
                doneBtnText: 'Done',
                nextBtnText: 'Done',
                onNextClick: finish,
                onPopoverRender: popoverFooter(5, null)
            }
        });
    }

    async function loadTour() {
        await import('driver.js/dist/driver.css');
        const { driver } = await import('driver.js');
        tour = driver({
            animate: true,
            stagePadding: 2,
            allowClose: true,
            overlayClickBehavior: () => dismiss(stage ?? 'grid'),
            onDestroyed: () => {
                if (!suppressDismiss && get(state) === 'running') dismiss(stage ?? 'grid');
            }
        });
    }

    async function start() {
        onboarding.start();
        track('onboarding_started');
        await loadTour();
        if (get(state) === 'running') highlightGrid();
        else tour?.destroy();
    }

    async function replay() {
        if (!enabled) return;
        dismiss(stage ?? 'invitation');
        onboarding.replay();
        track('onboarding_replayed');
        if (!isImages) {
            await goto(routeHelpers.toImages(datasetId, collectionType, collectionId));
        }
        await loadTour();
        update();
    }

    function handoff(event: Event) {
        const detail = (event as CustomEvent<{ collectionId: string }>).detail;
        if (detail.collectionId !== collectionId || stage !== 'tile') return;
        suppressDismiss = true;
        onboarding.openingSample();
        tour?.destroy();
        tour = undefined;
        stage = null;
        suppressDismiss = false;
    }

    function update() {
        if (activeCollectionId !== null && collectionId !== activeCollectionId) {
            dismiss(stage ?? 'navigation');
        }
        activeCollectionId = collectionId;
        if (get(state) === 'unseen') void offerInvitation();
        if (get(state) === 'running' && !stage && isImages && tile()) highlightGrid();
        if (
            get(state) === 'opening_sample' &&
            isSampleDetails &&
            visible('[data-onboarding-detail]') &&
            !loadingDetail
        ) {
            loadingDetail = true;
            void loadTour()
                .then(highlightDetail)
                .finally(() => {
                    loadingDetail = false;
                });
        }
        if (get(state) === 'running' && !isImages && stage !== 'detail') dismiss('navigation');
    }

    onMount(() => {
        const observer = new MutationObserver(update);
        observer.observe(document.body, { childList: true, subtree: true });
        window.addEventListener('onboarding:opening-sample', handoff);
        update();
        return () => {
            observer.disconnect();
            window.removeEventListener('onboarding:opening-sample', handoff);
        };
    });

    $effect(() => {
        void enabled;
        void isImages;
        void isSampleDetails;
        void collectionId;
        if (replayRequest > replaySeen) {
            replaySeen = replayRequest;
            void replay();
        } else if (typeof document !== 'undefined') {
            queueMicrotask(update);
        }
    });

    onDestroy(() => {
        if (get(state) === 'running' || get(state) === 'opening_sample') dismiss('navigation');
    });
</script>

{#if $state === 'invited'}
    <Invitation onStart={start} onDismiss={() => dismiss('invitation')} />
{/if}

<style>
    /* Higher specificity (body + class) so these win over driver.js's dynamically
       injected CSS, which loads after component styles and would otherwise override
       same-specificity rules. */
    :global(body .driver-popover) {
        background-color: hsl(var(--card));
        color: hsl(var(--card-foreground));
        border: 1px solid hsl(var(--border-hard));
        border-radius: var(--radius);
        --driver-popover-font-family: 'Open Sans', sans-serif;
        box-shadow: 0 4px 16px rgb(0 0 0 / 0.15);
        padding: 16px;
        min-width: 260px;
        max-width: 320px;
    }

    :global(body .driver-popover-title) {
        font-size: 15px;
        font-weight: 600;
        color: hsl(var(--card-foreground));
    }

    :global(body .driver-popover-description) {
        font-size: 13px;
        color: hsl(var(--muted-foreground));
        line-height: 1.5;
    }

    :global(body .driver-popover-footer) {
        margin-top: 12px;
        flex-wrap: wrap;
        gap: 6px;
    }

    :global(body .driver-tour-dots) {
        flex-basis: 100%;
        display: flex;
        gap: 5px;
        justify-content: center;
        padding-bottom: 2px;
    }

    :global(body .driver-tour-dot) {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: hsl(var(--border-hard));
        flex-shrink: 0;
    }

    :global(body .driver-tour-dot--active) {
        background-color: hsl(var(--primary));
    }

    :global(body .driver-popover-footer-btn) {
        background-color: transparent;
        color: hsl(var(--muted-foreground));
        border: 1px solid hsl(var(--border-hard));
        border-radius: calc(var(--radius) - 2px);
        font-size: 12px;
        padding: 4px 10px;
    }

    :global(body .driver-popover-footer-btn:hover),
    :global(body .driver-popover-footer-btn:focus) {
        background-color: hsl(var(--muted));
        color: hsl(var(--foreground));
    }

    :global(body .driver-popover-next-btn),
    :global(body .driver-tour-open-btn) {
        background-color: hsl(var(--primary));
        color: hsl(var(--primary-foreground));
        border-color: hsl(var(--primary));
    }

    :global(body .driver-popover-next-btn:hover),
    :global(body .driver-popover-next-btn:focus),
    :global(body .driver-tour-open-btn:hover),
    :global(body .driver-tour-open-btn:focus) {
        background-color: hsl(var(--primary) / 0.85);
        color: hsl(var(--primary-foreground));
    }

/* Color only the visible border for each arrow direction.
       Driver.js sets the other three to transparent in the same rule — those
       must be left alone or the triangle breaks. */
    :global(body .driver-popover-arrow-side-top) {
        border-top-color: hsl(var(--border-hard));
    }
    :global(body .driver-popover-arrow-side-bottom) {
        border-bottom-color: hsl(var(--border-hard));
    }
    :global(body .driver-popover-arrow-side-left) {
        border-left-color: hsl(var(--border-hard));
    }
    :global(body .driver-popover-arrow-side-right) {
        border-right-color: hsl(var(--border-hard));
    }
</style>
