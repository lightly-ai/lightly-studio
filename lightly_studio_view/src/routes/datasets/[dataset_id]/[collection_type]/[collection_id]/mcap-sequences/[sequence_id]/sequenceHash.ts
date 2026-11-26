export const getTickNumberFromHash = (hash: string): number => {
    const tickValue = new URLSearchParams(hash.slice(1)).get('tick');
    const tickNumber = Number(tickValue);
    return Number.isSafeInteger(tickNumber) && tickNumber > 0 ? tickNumber : 1;
};

export const getCameraFromHash = (hash: string): string | undefined =>
    new URLSearchParams(hash.slice(1)).get('camera') || undefined;

export const buildSequenceHash = ({ tick, camera }: { tick: number; camera?: string }): string => {
    const params = new URLSearchParams({ tick: String(tick) });
    if (camera) params.set('camera', camera);
    return params.toString();
};
