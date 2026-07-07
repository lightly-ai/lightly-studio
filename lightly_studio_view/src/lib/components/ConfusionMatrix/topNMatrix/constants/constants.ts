import { NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL } from '../../types';
import type { ClassSortOption } from '../types';

/**
 * Shared constants and types: client-side top-N class selection
 * with "(other)" aggregation. The functions in this module are pure and have
 * no ECharts dependency.
 */

/** Aggregate bucket label for classes hidden from a filtered matrix. */
export const OTHER_LABEL = '(other)';

/** Sentinel no-ground-truth / no-prediction labels that are not real classes. */
export const SENTINELS = new Set<string>([NO_GROUND_TRUTH_ROW_LABEL, NO_PREDICTION_COL_LABEL]);

export const CLASS_SORT_LABELS: Record<ClassSortOption, string> = {
    'most-confused': 'Most confused',
    'least-confused': 'Least confused',
    'most-samples': 'Most ground truth samples',
    alphabetical: 'Alphabetical'
};
