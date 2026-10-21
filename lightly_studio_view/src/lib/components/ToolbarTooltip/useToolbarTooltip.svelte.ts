interface UseToolbarTooltipParams {
    getTrigger: () => HTMLElement | undefined;
    getPosition: () => 'right' | 'top';
    tooltipId: string;
}

export function useToolbarTooltip({ getTrigger, getPosition, tooltipId }: UseToolbarTooltipParams) {
    let visible = $state(false);
    let triggerRect = $state<DOMRect | null>(null);
    const offset = 12;

    function updateRect() {
        triggerRect = getTrigger()?.getBoundingClientRect() ?? null;
    }

    function show() {
        updateRect();
        visible = true;
    }

    function hide() {
        visible = false;
    }

    function showOnFocus(event: FocusEvent) {
        if (event.target instanceof HTMLElement && event.target.matches(':focus-visible')) show();
    }

    // Follow the trigger while open and describe its control for assistive technology.
    $effect(() => {
        if (!visible) return;
        const control = getTrigger()?.querySelector<HTMLElement>('button, [tabindex]');
        const previous = control?.getAttribute('aria-describedby') ?? null;
        control?.setAttribute(
            'aria-describedby',
            previous ? `${previous} ${tooltipId}` : tooltipId
        );
        window.addEventListener('resize', updateRect);
        window.addEventListener('scroll', updateRect, true);
        return () => {
            if (previous === null) control?.removeAttribute('aria-describedby');
            else control?.setAttribute('aria-describedby', previous);
            window.removeEventListener('resize', updateRect);
            window.removeEventListener('scroll', updateRect, true);
        };
    });

    return {
        get visible() {
            return visible && triggerRect !== null;
        },
        get style() {
            if (!triggerRect) return '';
            if (getPosition() === 'top') {
                return `left: ${triggerRect.left + triggerRect.width / 2}px; top: ${triggerRect.top - offset}px; transform: translate(-50%, -100%);`;
            }
            return `left: ${triggerRect.right + offset}px; top: ${triggerRect.top + triggerRect.height / 2}px; transform: translate(0, -50%);`;
        },
        show,
        hide,
        showOnFocus
    };
}

// Escape parents with hidden overflow, including the embedding plot panel.
export function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
        destroy() {
            node.remove();
        }
    };
}
