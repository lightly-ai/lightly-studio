/**
 * Which part of the annotation card shows: the compact view, the class search or the move list.
 * Esc goes back from a list to the compact view. Call during component init.
 */
export const useCardView = (getIsActive: () => boolean) => {
    let view = $state<'compact' | 'search' | 'move'>('compact');

    const show = (next: typeof view) => {
        view = next;
    };
    // The lists handle Esc only while their input has focus. Capture phase, so it also wins
    // over the card's close and the panel's tool switch.
    const handleWindowKeydown = (event: KeyboardEvent) => {
        if (!getIsActive() || view === 'compact' || event.key !== 'Escape' || event.repeat) return;
        if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
        event.preventDefault();
        event.stopPropagation();
        view = 'compact';
    };

    return {
        get current() {
            return view;
        },
        show,
        handleWindowKeydown
    };
};
