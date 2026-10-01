/** Formats a ratio (0–1) as a percentage; tiny non-zero shares render as `<0.1%`. */
export const formatPercent = (ratio: number): string => {
    const percent = ratio * 100;
    if (percent > 0 && percent < 0.1) return '<0.1%';
    return `${percent.toFixed(1)}%`;
};
