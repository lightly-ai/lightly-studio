import { useSettings } from '$lib/hooks/useSettings';
import { isInputElement } from '$lib/utils';
import { derived, writable } from 'svelte/store';

const isHidden = writable(false);

export function useHideAnnotations() {
    const { settingsStore } = useSettings();

    const hideKey = derived(settingsStore, ($settings) => {
        return $settings.key_hide_annotations || 'v';
    });

    const handleKeyEvent = (event: KeyboardEvent) => {
        if (isInputElement(event.target)) {
            return;
        }

        let currentHideKey = '';
        const unsubscribe = hideKey.subscribe((value) => {
            currentHideKey = value;
        });
        unsubscribe();

        if (event.key === currentHideKey) {
            isHidden.set(event.type === 'keydown');
        }
    };

    return {
        isHidden,
        handleKeyEvent
    };
}
