import type { BoundingBox } from '$lib/types';
import { isOverlayTarget, isTextInputTarget } from '$lib/utils';

export interface Rect {
    left: number;
    top: number;
    right: number;
    bottom: number;
}

interface PlacePanelParams {
    /** Screen rectangle of the selected box. */
    box: Rect;
    /** Screen rectangle of the visible canvas. */
    canvas: Rect;
    panel: { width: number; height: number };
    gap?: number;
}

/**
 * Places the panel beside the box, right of it if it fits, else left of it, and keeps it on the
 * canvas. The panel covers the box only when neither side has room.
 */
export const placePanel = ({ box, canvas, panel, gap = 8 }: PlacePanelParams) => {
    const rightLeft = box.right + gap;
    const leftLeft = box.left - gap - panel.width;
    let left: number;
    if (rightLeft + panel.width <= canvas.right) {
        left = rightLeft;
    } else if (leftLeft >= canvas.left) {
        left = leftLeft;
    } else {
        left = canvas.right - panel.width;
    }
    left = clamp(left, canvas.left, canvas.right - panel.width);
    const top = clamp(box.top, canvas.top, canvas.bottom - panel.height);
    return { left, top };
};

/** Maps an image-space box to screen pixels with the scale and translation of a DOM matrix. */
export const imageRectToScreen = (
    bbox: BoundingBox,
    matrix: Pick<DOMMatrix, 'a' | 'd' | 'e' | 'f'>
): Rect => ({
    left: bbox.x * matrix.a + matrix.e,
    top: bbox.y * matrix.d + matrix.f,
    right: (bbox.x + bbox.width) * matrix.a + matrix.e,
    bottom: (bbox.y + bbox.height) * matrix.d + matrix.f
});

type KeyPress = Pick<KeyboardEvent, 'key' | 'target' | 'repeat' | 'altKey' | 'ctrlKey' | 'metaKey'>;

const isPlainPress = (event: KeyPress) =>
    !event.repeat &&
    !event.altKey &&
    !event.ctrlKey &&
    !event.metaKey &&
    !isTextInputTarget(event.target) &&
    !isOverlayTarget(event.target);

/** Whether a key press should delete the selected box. */
export const isDeleteKey = (event: KeyPress): boolean =>
    (event.key === 'Delete' || event.key === 'Backspace') && isPlainPress(event);

/** Whether a key press should start the class search, unless it is a shortcut key. */
export const isSearchStartKey = (event: KeyPress, shortcutKeys: string[]): boolean =>
    /^[\p{L}\p{N}]$/u.test(event.key) &&
    !shortcutKeys.includes(event.key.toLowerCase()) &&
    isPlainPress(event);

export const SHORTCUT_SETTING_KEYS = [
    'key_hide_annotations',
    'key_toggle_edit_mode',
    'key_toolbar_selection',
    'key_toolbar_drag',
    'key_toolbar_bounding_box',
    'key_toolbar_segmentation_mask',
    'key_toolbar_slic',
    'key_toolbar_brush',
    'key_toolbar_eraser'
] as const;

/** The lowercase shortcut keys that are set, in the order of `SHORTCUT_SETTING_KEYS`. */
export const getShortcutKeys = (
    settings: Partial<Record<(typeof SHORTCUT_SETTING_KEYS)[number], string | null>>
): string[] =>
    SHORTCUT_SETTING_KEYS.flatMap((key) => {
        const value = settings[key];
        return value ? [value.toLowerCase()] : [];
    });

const byName = (a: string, b: string) => a.localeCompare(b);

/** 0 for an exact match, 1 for a prefix, 2 for a substring, null for no match. */
const matchTier = (name: string, query: string): number | null => {
    const lower = name.toLowerCase();
    if (lower === query) return 0;
    if (lower.startsWith(query)) return 1;
    return lower.includes(query) ? 2 : null;
};

/**
 * Filters the class names by the query: exact match, then prefix, then substring. Recent classes
 * come first within a tier, then alphabetical. `createName` is the trimmed query when no class
 * matches it exactly.
 */
export const matchClasses = ({
    names,
    recent,
    query
}: {
    names: string[];
    recent: string[];
    query: string;
}): { matches: string[]; createName: string | null } => {
    const trimmed = query.trim();
    const lowered = trimmed.toLowerCase();
    const recentRank = (name: string) => {
        const index = recent.indexOf(name);
        return index === -1 ? Infinity : index;
    };
    const ranked = names.flatMap((name) => {
        const tier = matchTier(name, lowered);
        return tier === null ? [] : [{ name, tier }];
    });
    ranked.sort(
        (a, b) =>
            a.tier - b.tier ||
            (recentRank(a.name) === recentRank(b.name)
                ? byName(a.name, b.name)
                : recentRank(a.name) - recentRank(b.name))
    );
    const hasExact = names.some((name) => name.toLowerCase() === lowered);
    return {
        matches: ranked.map(({ name }) => name),
        createName: trimmed && !hasExact ? trimmed : null
    };
};

/** Filters the annotation sources by the query: prefix, then substring, then alphabetical. */
export const matchSources = <T extends { name: string }>({
    sources,
    query
}: {
    sources: T[];
    query: string;
}): T[] => {
    const lowered = query.trim().toLowerCase();
    const ranked = sources.flatMap((source) => {
        const tier = matchTier(source.name, lowered);
        return tier === null ? [] : [{ source, tier }];
    });
    ranked.sort((a, b) => a.tier - b.tier || byName(a.source.name, b.source.name));
    return ranked.map(({ source }) => source);
};

/** The recent classes to show as chips, without the current class. */
export const recentChips = (list: string[], current: string | null, max = 3): string[] =>
    list.filter((name) => name !== current).slice(0, max);

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max));
