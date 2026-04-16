import { writable } from 'svelte/store';

// Module-level store: shared across all components using this hook
const activeQueryText = writable<string>('');

export function useQueryLanguage() {
    const setQueryText = (text: string) => {
        activeQueryText.set(text);
    };

    const clearQueryText = () => {
        activeQueryText.set('');
    };

    return { activeQueryText, setQueryText, clearQueryText };
}
