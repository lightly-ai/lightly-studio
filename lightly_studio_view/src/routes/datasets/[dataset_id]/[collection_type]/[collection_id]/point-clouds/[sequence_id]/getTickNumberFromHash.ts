export const getTickNumberFromHash = (hash: string): number => {
    const tickValue = new URLSearchParams(hash.slice(1)).get('tick');
    const tickNumber = Number(tickValue);
    return Number.isSafeInteger(tickNumber) && tickNumber > 0 ? tickNumber : 1;
};
