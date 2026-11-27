/** Scrolls the element to the middle of its list whenever `active` turns true. */
export const scrollIntoViewWhen = (element: HTMLElement, active: boolean) => {
    const scroll = (isActive: boolean) => {
        if (!isActive) return;
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        element.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
    };
    scroll(active);
    return { update: scroll };
};
