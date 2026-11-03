import { describe, expect, it } from 'vitest';
import { formatTagAddToast, formatTagRemoveToast } from './tagToasts';

describe('tag toasts', () => {
    it('count only the changed items', () => {
        expect(formatTagAddToast('asdfasdf', 2, 3)).toBe("Added 'asdfasdf' to 2 items");
        expect(formatTagAddToast('a', 1, 3)).toBe("Added 'a' to 1 item");
        expect(formatTagRemoveToast('b', 1, 3)).toBe("Removed 'b' from 1 item");
    });

    it('say so when nothing changed', () => {
        expect(formatTagAddToast('asdfasdf', 0, 3)).toBe("All 3 items already have 'asdfasdf'");
        expect(formatTagRemoveToast('b', 0, 3)).toBe("None of the 3 items have 'b'");
    });
});
