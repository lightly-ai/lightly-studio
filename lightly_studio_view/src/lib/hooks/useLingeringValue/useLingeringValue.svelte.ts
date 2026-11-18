export interface UseLingeringValueReturn<T> {
    readonly current: T | null;
}

// Shows a value at once and keeps it for `hideDelayMs` after it clears. This keeps a hover hint
// from blinking while the cursor crosses the gaps between points. While `getHideAtOnce` is true,
// a cleared value goes away without the delay.
export function useLingeringValue<T>(
    getValue: () => T | null,
    hideDelayMs: number,
    getHideAtOnce: () => boolean = () => false
): UseLingeringValueReturn<T> {
    let shown = $state.raw<T | null>(null);
    $effect(() => {
        const value = getValue();
        if (value !== null) {
            shown = value;
            return;
        }
        if (getHideAtOnce()) {
            shown = null;
            return;
        }
        const timer = setTimeout(() => {
            shown = null;
        }, hideDelayMs);
        return () => clearTimeout(timer);
    });
    return {
        get current() {
            return shown;
        }
    };
}
