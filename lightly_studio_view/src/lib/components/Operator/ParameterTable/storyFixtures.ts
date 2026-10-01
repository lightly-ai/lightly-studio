import type { OperatorParameterColumn } from '$lib/hooks';
import { column } from '../fixtures';
import type { ParameterTableRow } from '../parameterTypeConfig';

/** The two `str` columns a segmentation operator declares. `column()` already covers `prompt`. */
export const promptColumns: OperatorParameterColumn[] = [
    column({ description: 'What to segment in the image.' }),
    column({ name: 'label', description: 'Label for the masks.', required: false })
];

/** Every cell type, and more columns than the dialog fits, so the table scrolls sideways. */
export const wideColumns: OperatorParameterColumn[] = [
    ...promptColumns,
    column({ name: 'limit', paramType: 'int', default: 5, required: false }),
    column({ name: 'threshold', paramType: 'float', default: 0.5, required: false }),
    column({ name: 'enabled', paramType: 'bool', default: true, required: false })
];

/** Seven rows: past the four the table shows before it starts scrolling vertically. */
export const promptRows: ParameterTableRow[] = [
    { prompt: 'person', label: 'pedestrian' },
    { prompt: 'car', label: 'vehicle' },
    { prompt: 'dog', label: 'animal' },
    { prompt: 'tree', label: 'plant' },
    { prompt: 'bicycle', label: 'vehicle' },
    { prompt: 'traffic light', label: 'signal' },
    { prompt: 'building', label: 'structure' }
];

/** The same rows with a cell for every `wideColumns` column, so no cell reads as missing. */
export const wideRows: ParameterTableRow[] = promptRows.map((row, index) => ({
    ...row,
    limit: index + 1,
    threshold: 0.5,
    enabled: index % 2 === 0
}));
