<script lang="ts">
    import { goto } from '$app/navigation';
    import { routeHelpers } from '$lib/routes';
    import { usePostHog, useOnboarding, TOUR_VERSION } from '$lib/hooks';
    import { get } from 'svelte/store';
    import { onDestroy, onMount } from 'svelte';
    import {
        type TourRef,
        tileElement,
        visible,
        createTourSteps,
        DEFAULT_STEP_PLAN
    } from './Onboarding.steps';
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
    }

    let {
        enabled,
        isImages,
        isSampleDetails,
        collectionId,
        collectionType,
        datasetId,
        sampleCount
    }: Props = $props();

    const onboarding = useOnboarding();
    const { state } = onboarding;
    const { ready, trackEvent } = usePostHog();

    const ref: TourRef = {
        tour: undefined,
        stage: null,
        menuHighlightCleanup: null,
        stepPlan: DEFAULT_STEP_PLAN
    };
    let trackingReady = false;
    let checkingEligibility = false;
    let suppressDismiss = false;
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

    function eligible(): boolean {
        return enabled && isImages && sampleCount > 0 && !!tileElement();
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

    function dismiss(dismissalStage: string) {
        if (get(state) === 'finished' || get(state) === 'unseen') return;
        steps.cleanupMenuHighlight();
        track('onboarding_dismissed', { dismissal_stage: dismissalStage });
        onboarding.dismiss();
        ref.stage = null;
        ref.tour?.destroy();
        ref.tour = undefined;
    }

    function finish() {
        steps.cleanupMenuHighlight();
        track('onboarding_completed');
        onboarding.complete();
        ref.stage = null;
        ref.tour?.destroy();
        ref.tour = undefined;
    }

    const steps = createTourSteps({
        ref,
        eligible,
        tile: tileElement,
        isSampleDetails: () => isSampleDetails,
        onSkip: skipTour,
        onFinish: finish,
        onStartOnboarding: onboarding.start,
        onOpenFirstSample: onboarding.dispatchOpenFirstSample
    });

    async function loadTour() {
        await import('driver.js/dist/driver.css');
        const { driver } = await import('driver.js');
        ref.tour = driver({
            animate: true,
            stagePadding: 2,
            allowClose: true,
            overlayOpacity: 0.85,
            overlayClickBehavior: () => dismiss(ref.stage ?? 'grid'),
            onDestroyed: () => {
                if (!suppressDismiss && get(state) === 'running') dismiss(ref.stage ?? 'grid');
            }
        });
    }

    async function start() {
        onboarding.start();
        track('onboarding_started');
        await loadTour();
        if (get(state) === 'running') steps.highlightGrid();
        else ref.tour?.destroy();
    }

    async function replay() {
        if (!enabled) return;
        // Skip dismiss when there is no active session to clean up.
        if (get(state) !== 'unseen') dismiss(ref.stage ?? 'invitation');
        if (!isImages) {
            // Defer replay() until after navigation so that update() triggered
            // by the route change cannot dismiss the new session.
            await goto(routeHelpers.toImages(datasetId, collectionType, collectionId));
        }
        onboarding.replay();
        track('onboarding_replayed');
        await loadTour();
        update();
    }

    function handoff(handoffCollectionId: string) {
        if (handoffCollectionId !== collectionId || ref.stage !== 'tile') return;
        suppressDismiss = true;
        onboarding.openingSample();
        ref.tour?.destroy();
        ref.tour = undefined;
        ref.stage = null;
        suppressDismiss = false;
    }

    function update() {
        if (activeCollectionId !== null && collectionId !== activeCollectionId) {
            dismiss(ref.stage ?? 'navigation');
        }
        activeCollectionId = collectionId;
        if (get(state) === 'unseen') void offerInvitation();
        if (get(state) === 'running' && !ref.stage && isImages && tileElement())
            steps.highlightGrid();
        if (
            get(state) === 'opening_sample' &&
            isSampleDetails &&
            visible('[data-onboarding-detail]') &&
            !loadingDetail
        ) {
            loadingDetail = true;
            void loadTour()
                .then(steps.highlightDetail)
                .finally(() => {
                    loadingDetail = false;
                });
        }
        if (get(state) === 'running' && !isImages && ref.stage !== 'detail') dismiss('navigation');
    }

    let replaySeen = 0;

    onMount(() => {
        const domObserver = new MutationObserver(update);
        domObserver.observe(document.body, { childList: true, subtree: true });
        const unregisterHandoff = onboarding.registerOpeningSampleHandler(handoff);
        const unsubscribeReplay = onboarding.replayRequested.subscribe((n) => {
            if (n > replaySeen) {
                replaySeen = n;
                void replay();
            }
        });
        update();
        return () => {
            domObserver.disconnect();
            unregisterHandoff();
            unsubscribeReplay();
        };
    });

    $effect(() => {
        void enabled;
        void isImages;
        void isSampleDetails;
        void collectionId;
        if (typeof document !== 'undefined') {
            queueMicrotask(update);
        }
    });

    onDestroy(() => {
        if (get(state) === 'running' || get(state) === 'opening_sample') dismiss('navigation');
    });
</script>

{#if $state === 'invited'}
    <div class="fixed inset-0 z-[10000] bg-black/85"></div>
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
        padding-bottom: 6px;
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
