// The four texts of the plot axes as the user types them.
export const createEmptyTextAxesDraft = () => ({
    xNegative: '',
    xPositive: '',
    yNegative: '',
    yPositive: ''
});

type TextAxesDraft = ReturnType<typeof createEmptyTextAxesDraft>;

// Returns the trimmed text axes when all four texts are filled, otherwise null.
export const toTextAxes = (draft: TextAxesDraft) => {
    if (!Object.values(draft).every((text) => text.trim())) return null;
    return {
        x: { negative: draft.xNegative.trim(), positive: draft.xPositive.trim() },
        y: { negative: draft.yNegative.trim(), positive: draft.yPositive.trim() }
    };
};

type TextAxes = NonNullable<ReturnType<typeof toTextAxes>>;

// True when `b` has the same four texts as `a`.
export const areTextAxesEqual = (a: TextAxes, b: TextAxes | null): boolean =>
    b !== null &&
    a.x.negative === b.x.negative &&
    a.x.positive === b.x.positive &&
    a.y.negative === b.y.negative &&
    a.y.positive === b.y.positive;
