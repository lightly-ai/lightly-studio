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

// Returns one marker for each corner of the plot, bottom row first. A marker combines one text of
// the x axis with one text of the y axis. The embedder gets a natural phrase ("young sad"), and
// the label shows the two prompts ("young + sad").
export const toCornerMarkers = ({ x, y }: TextAxes): { label: string; text: string }[] => {
    const markers = [y.negative, y.positive].flatMap((yText) =>
        [x.negative, x.positive].map((xText) => ({
            label: `${xText} + ${yText}`,
            text: `${xText} ${yText}`
        }))
    );
    // An axis with the same text twice gives the same marker twice. A marker label must be unique.
    return markers.filter(
        (marker, index) => markers.findIndex(({ label }) => label === marker.label) === index
    );
};
