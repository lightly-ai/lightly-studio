import { describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
    getKeywordHover: vi.fn(),
    getFieldHover: vi.fn()
}));

vi.mock('monaco-editor', () => ({}));
vi.mock('./getKeywordHover', () => ({ getKeywordHover: mocks.getKeywordHover }));
vi.mock('./getFieldHover', () => ({ getFieldHover: mocks.getFieldHover }));

describe('getHover', () => {
    it('prefers keyword hover when available', async () => {
        const { getHover } = await import('./getHover');
        const model = {} as never;
        const position = {} as never;
        const keywordHover = { contents: [{ value: 'keyword' }], range: null };
        mocks.getKeywordHover.mockReturnValueOnce(keywordHover);

        expect(getHover(model, position)).toBe(keywordHover as never);
        expect(mocks.getFieldHover).not.toHaveBeenCalled();
    });

    it('falls back to field hover when keyword hover is null', async () => {
        const { getHover } = await import('./getHover');
        const model = {} as never;
        const position = {} as never;
        const fieldHover = { contents: [{ value: 'field' }], range: null };
        mocks.getKeywordHover.mockReturnValueOnce(null);
        mocks.getFieldHover.mockReturnValueOnce(fieldHover);

        expect(getHover(model, position)).toBe(fieldHover as never);
        expect(mocks.getFieldHover).toHaveBeenCalledWith(model, position);
    });
});
