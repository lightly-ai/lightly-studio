interface UseHeldActiveFieldsReturn {
    /** Whether the field counts as active for the order of the rows. */
    isActive: (id: string, active: boolean) => boolean;
    onpointerenter: () => void;
    onpointerleave: () => void;
    onkeydown: () => void;
    onfocusout: (event: FocusEvent) => void;
}

/**
 * Holds the order of the rows while the user works in them, so a row does not move under the
 * pointer. The order updates when the pointer leaves the rows, or after keyboard input, when
 * the focus leaves them. Safari does not focus a clicked button, so the pointer decides.
 */
export function useHeldActiveFields(getActiveIds: () => string[]): UseHeldActiveFieldsReturn {
    let held = $state<Set<string>>();
    let pointerInside = false;
    let keyboardInside = false;

    const hold = () => {
        held ??= new Set(getActiveIds());
    };
    const release = () => {
        if (!pointerInside && !keyboardInside) held = undefined;
    };

    return {
        isActive: (id, active) => (held ? held.has(id) : active),
        onpointerenter: () => {
            pointerInside = true;
            hold();
        },
        onpointerleave: () => {
            pointerInside = false;
            release();
        },
        onkeydown: () => {
            keyboardInside = true;
            hold();
        },
        onfocusout: (event) => {
            const rows = event.currentTarget as HTMLElement;
            if (rows.contains(event.relatedTarget as Node | null)) return;
            keyboardInside = false;
            release();
        }
    };
}
