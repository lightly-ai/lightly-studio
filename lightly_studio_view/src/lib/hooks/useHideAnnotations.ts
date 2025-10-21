import { useSettings } from '$lib/hooks/useSettings';
import { derived, writable } from 'svelte/store';

// Create a writable store for tracking visibility state
const isHidden = writable(false);

export function useHideAnnotations() {
    const { settingsStore } = useSettings();

    // Create a derived store that will update whenever the shortcuts change
    const hideKey = derived(settingsStore, ($settings) => {
        return $settings.key_hide_annotations || 'v';
    });

    // Handle showing/hiding annotations based on key events
    const handleKeyEvent = (event: KeyboardEvent) => {
        // Don't trigger shortcuts when typing in input fields
        if (
            event.target instanceof HTMLInputElement ||
            event.target instanceof HTMLTextAreaElement ||
            event.target instanceof HTMLSelectElement
        ) {
            return;
        }

        // Subscribe to the derived store to get the current value
        let currentHideKey: string;
        const unsubscribe = hideKey.subscribe((value) => {
            currentHideKey = value;
        });
        unsubscribe(); // Clean up the subscription immediately

        if (event.key === currentHideKey) {
            isHidden.set(event.type === 'keydown');
        }
    };

    return {
        isHidden,
        handleKeyEvent
    };
}
