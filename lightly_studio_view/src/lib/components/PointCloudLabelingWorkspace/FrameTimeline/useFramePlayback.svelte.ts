import type { FrameNavigation } from '../types';

const DEFAULT_INTERVAL_MS = 200;

/**
 * Owns play/pause state and steps `navigation` forward on an interval while playing.
 *
 * A tick is skipped, not queued, when a frame read is still in flight, so playback never piles
 * up calls during a slow read; it stops on its own once the known frames are exhausted. `toggle`
 * is async so a caller-supplied guard (e.g. an unsaved-edits prompt) can block *starting*
 * playback; once playing, each automatic step is not re-guarded.
 *
 * @param getNavigation - Thunk so this reacts to a `navigation` prop that changes identity.
 */
export function useFramePlayback(
    getNavigation: () => FrameNavigation | undefined,
    intervalMs = DEFAULT_INTERVAL_MS
) {
    let isPlaying = $state(false);

    const isAtLastFrame = $derived.by(() => {
        const navigation = getNavigation();
        return (
            !!navigation && !navigation.hasMore && navigation.position >= navigation.frameCount - 1
        );
    });

    async function toggle(guard?: () => boolean | Promise<boolean>) {
        if (isPlaying) {
            isPlaying = false;
            return;
        }
        const navigation = getNavigation();
        if (!navigation || isAtLastFrame) return;
        if (guard && !(await guard())) return;
        isPlaying = true;
    }

    $effect(() => {
        if (!isPlaying) return;
        const interval = setInterval(() => {
            const navigation = getNavigation();
            if (!navigation || navigation.isLoading) return;
            if (isAtLastFrame) {
                isPlaying = false;
                return;
            }
            navigation.next();
        }, intervalMs);
        return () => clearInterval(interval);
    });

    return {
        get isPlaying() {
            return isPlaying;
        },
        get isAtLastFrame() {
            return isAtLastFrame;
        },
        toggle
    };
}
