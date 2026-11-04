import { fromStore } from 'svelte/store';
import { useSettings } from '$lib/hooks/useSettings';

/**
 * The saved "Color by" mode while the tree is on. `current` is undefined while the tree is off,
 * so callers keep the automatic rule.
 */
export const useTreeColorMode = (isEnabled: () => boolean = () => true) => {
    const mode = fromStore(useSettings().annotationColorModeStore);

    return {
        get current() {
            return isEnabled() ? mode.current : undefined;
        }
    };
};
