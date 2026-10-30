/** Tracks browser fullscreen for the workspace's root element. */
export function useWorkspaceFullscreen() {
    let containerEl = $state<HTMLDivElement>();
    let isFullscreen = $state(false);

    const handleFullscreenChange = () => {
        isFullscreen = document.fullscreenElement === containerEl;
    };
    const toggleFullscreen = async () => {
        if (!containerEl) return;
        if (document.fullscreenElement) await document.exitFullscreen();
        else await containerEl.requestFullscreen();
    };

    $effect(() => {
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    });

    return {
        get containerEl() {
            return containerEl;
        },
        set containerEl(value) {
            containerEl = value;
        },
        get isFullscreen() {
            return isFullscreen;
        },
        toggleFullscreen
    };
}
