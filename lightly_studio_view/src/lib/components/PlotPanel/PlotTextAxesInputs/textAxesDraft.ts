// The four texts of the plot axes as the user types them.
export const createEmptyTextAxesDraft = () => ({
    xNegative: '',
    xPositive: '',
    yNegative: '',
    yPositive: ''
});

type TextAxesDraft = ReturnType<typeof createEmptyTextAxesDraft>;

// Returns the text axes when all four texts are filled, otherwise null.
export const toTextAxes = (draft: TextAxesDraft) => {
    const xNegative = draft.xNegative.trim();
    const xPositive = draft.xPositive.trim();
    const yNegative = draft.yNegative.trim();
    const yPositive = draft.yPositive.trim();
    if (!xNegative || !xPositive || !yNegative || !yPositive) {
        return null;
    }
    return {
        x: { negative: xNegative, positive: xPositive },
        y: { negative: yNegative, positive: yPositive }
    };
};
