import { writable } from 'svelte/store';

export const ONBOARDING_STORAGE_KEY = 'lightly-studio:onboarding-invitation:v1';
export const TOUR_VERSION = 1;

export type OnboardingState = 'unseen' | 'invited' | 'running' | 'opening_sample' | 'finished';

let invitationShownThisSession = false;
const state = writable<OnboardingState>('unseen');
const replayRequested = writable(0);
let openFirstSampleHandler: (() => void) | null = null;
let openingSampleHandler: ((collectionId: string) => void) | null = null;

function invite(): boolean {
    if (invitationShownThisSession) return false;
    try {
        if (localStorage.getItem(ONBOARDING_STORAGE_KEY)) return false;
        localStorage.setItem(ONBOARDING_STORAGE_KEY, 'shown');
    } catch {
        // The session guard still prevents repeated invitations when storage is unavailable.
    }
    invitationShownThisSession = true;
    state.set('invited');
    return true;
}

export function useOnboarding() {
    return {
        state,
        invite,
        start: () => state.set('running'),
        openingSample: () => state.set('opening_sample'),
        dismiss: () => state.set('finished'),
        complete: () => state.set('finished'),
        replay: () => state.set('running'),
        /** Signal Onboarding to replay the tour (e.g. from the header menu). */
        requestReplay: () => replayRequested.update((n) => n + 1),
        replayRequested,
        /** Register the handler that opens the first sample when driver.js fires its button. */
        registerOpenFirstSampleHandler: (handler: () => void): (() => void) => {
            openFirstSampleHandler = handler;
            return () => {
                openFirstSampleHandler = null;
            };
        },
        dispatchOpenFirstSample: () => openFirstSampleHandler?.(),
        /** Register the handler that intercepts navigation-to-sample during the tour. */
        registerOpeningSampleHandler: (handler: (collectionId: string) => void): (() => void) => {
            openingSampleHandler = handler;
            return () => {
                openingSampleHandler = null;
            };
        },
        dispatchOpeningSample: (collectionId: string) => openingSampleHandler?.(collectionId)
    };
}
