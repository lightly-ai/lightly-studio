export const getSmartSelectHint = ({
    positivePoints,
    negativePoints,
    boxes
}: {
    positivePoints: boolean;
    negativePoints: boolean;
    boxes: boolean;
}): string => {
    const actions = [
        positivePoints && 'click to add',
        negativePoints && 'shift-click to remove',
        boxes && 'drag to box'
    ].filter((action): action is string => Boolean(action));
    const hint = actions.join(', ');
    return `${hint.charAt(0).toUpperCase()}${hint.slice(1)}.`;
};
