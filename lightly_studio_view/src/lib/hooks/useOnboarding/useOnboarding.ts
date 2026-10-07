import { writable } from 'svelte/store';

export const ONBOARDING_STORAGE_KEY = 'lightly-studio:onboarding-invitation:v1';
export const TOUR_VERSION = 1;

export type OnboardingState = 'unseen' | 'invited' | 'running' | 'opening_sample' | 'finished';

let invitationShownThisSession = false;

export function useOnboarding() {
    const state = writable<OnboardingState>('unseen');

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

    return {
        state,
        invite,
        start: () => state.set('running'),
        openingSample: () => state.set('opening_sample'),
        dismiss: () => state.set('finished'),
        complete: () => state.set('finished'),
        replay: () => state.set('running')
    };
}
