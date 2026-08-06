/**
 * Split `total` into per-split counts using the largest-remainder method.
 *
 * Mirrors the backend `partition_counts` so the previewed counts match what the
 * server will actually assign. Each split gets the floor of its exact
 * proportional share, then the leftover units go to the splits with the largest
 * fractional remainder, guaranteeing the counts sum exactly to `total`.
 */
export function partitionCounts(
    total: number,
    sizes: Record<string, number>
): Record<string, number> {
    const names = Object.keys(sizes);
    const sizeSum = names.reduce((sum, name) => sum + sizes[name], 0);
    if (sizeSum <= 0 || total <= 0) {
        return Object.fromEntries(names.map((name) => [name, 0]));
    }

    const exactShares = names.map((name) => (total * sizes[name]) / sizeSum);
    const counts = exactShares.map((share) => Math.floor(share));
    const leftover = total - counts.reduce((sum, count) => sum + count, 0);

    const orderByRemainder = names
        .map((_, index) => index)
        .sort((a, b) => exactShares[b] - counts[b] - (exactShares[a] - counts[a]));
    for (let i = 0; i < leftover; i++) {
        counts[orderByRemainder[i]] += 1;
    }

    return Object.fromEntries(names.map((name, index) => [name, counts[index]]));
}
