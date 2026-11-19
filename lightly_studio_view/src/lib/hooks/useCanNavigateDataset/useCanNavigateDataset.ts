import useAuth from '$lib/hooks/useAuth/useAuth';

/**
 * Whether the current user may navigate the dataset (collection home, grids) from the UI.
 * Labelers work only inside their assigned batches, so they may not; every other role may,
 * and so may everyone without a role (standalone mode).
 */
export function useCanNavigateDataset(): boolean {
    return useAuth().user?.role !== 'labeler';
}
