import type { OperatorParameterColumn } from '$lib/hooks';
import { getCellConfig, isCellSubmittable, type ParameterTableRow } from '../parameterTypeConfig';

// Four rows before the table scrolls instead of growing the dialog: inputs are h-10 (2.5rem) and rows
// are gap-2 (0.5rem) apart, so four measure 4 * 2.5rem + 3 * 0.5rem = 11.5rem. The header shares the
// scroll container with the rows so the two scroll horizontally as one, so this also has to cover the
// header row (text-xs, 1rem), the gap below it (0.5rem) and the p-2 padding (1rem), giving
// 11.5 + 1 + 0.5 + 1 = 14rem. Beyond that the table scrolls itself instead of pushing the dialog
// footer out of view.
//
// The header's -mt-2 and pt-2 cancel each other in the flow — the box grows half a rem upward to cover
// the container's top padding while its negative margin pulls the same amount back — so the header
// still contributes only its 1rem of text here.
export const MAX_TABLE_HEIGHT = 'max-h-[14rem]';

/**
 * The narrowest a data column may get. An Input spends 1.5rem of its width on px-3, so 9rem leaves
 * about 15 characters of text — below that a prompt or label stops being readable. The dialog leaves
 * roughly 24rem for the table once its own padding is taken off, which fits the two columns today's
 * operators use; a third one starts scrolling instead of squeezing every cell.
 */
const MIN_COLUMN_WIDTH = '9rem';

/**
 * The frozen remove-button column: 2.5rem for the `size="icon"` button plus the 0.5rem of pl-2 that
 * gives a cell scrolling underneath somewhere to disappear behind the divider, rather than being cut
 * off flush against the icon. The cell's pr-2 is not counted because its -mr-2 makes the item resolve
 * 0.5rem wider than this track, and that surplus hangs off the *left* edge to cover the gutter — the
 * container's own right padding is covered by the cell's negative right inset instead. Stated outright
 * rather than left to `auto` because the header and the rows are separate grids that would each size an
 * `auto` track from their own contents, and the header's cell is empty — the two would not agree on a
 * width.
 */
const REMOVE_COLUMN_WIDTH = '3rem';

/**
 * Tailwind cannot compile a class built at runtime, so the column count goes through style. Data
 * columns share the width evenly until they hit MIN_COLUMN_WIDTH, past which the table scrolls
 * horizontally; the trailing track holds the remove button. `repeat(0, ...)` is invalid CSS and would
 * make the browser drop the whole declaration, so a table without columns gets that track alone.
 */
export const buildGridStyle = (columnCount: number): string =>
    columnCount > 0
        ? `grid-template-columns: repeat(${columnCount}, minmax(${MIN_COLUMN_WIDTH}, 1fr)) ${REMOVE_COLUMN_WIDTH}`
        : `grid-template-columns: ${REMOVE_COLUMN_WIDTH}`;

/**
 * The value a cell starts out with: the column default when it fits the column type, and the empty
 * value of that type otherwise. Column defaults arrive as `unknown` because a column can hold any
 * built-in type, so this is where they become a cell.
 */
export function buildCellDefault(column: OperatorParameterColumn): ParameterTableRow[string] {
    const { type } = getCellConfig(column);
    const empty = type === 'bool' ? false : '';
    const value = column.default;
    if (value === undefined || value === null) return empty;
    if (type === 'bool') return typeof value === 'boolean' ? value : empty;
    if (type === 'string') return typeof value === 'string' ? value : String(value);
    return typeof value === 'number' && Number.isFinite(value) ? value : empty;
}

/** A new row starts from the column defaults so the user only edits what they care about. */
export const buildBlankRow = (columns: OperatorParameterColumn[]): ParameterTableRow =>
    Object.fromEntries(columns.map((column) => [column.name, buildCellDefault(column)]));

/** A copy of `rows` with a single cell replaced. Rows are never mutated in place. */
export const replaceCell = (
    rows: ParameterTableRow[],
    index: number,
    name: string,
    value: ParameterTableRow[string]
): ParameterTableRow[] =>
    rows.map((row, rowIndex) => (rowIndex === index ? { ...row, [name]: value } : row));

/** Validation state of the table parameter the cell belongs to. */
interface TableValidationState {
    /** Whether the table parameter itself is required. */
    required: boolean;
    /** Whether the table parameter is currently blocking submission. */
    isMissing: boolean;
}

/**
 * Whether a cell should be flagged as invalid. An optional cell the backend would reject is flagged
 * on sight; an empty required one only once the table blocks submission, so new rows are not red.
 */
export const isCellInvalid = (
    row: ParameterTableRow,
    column: OperatorParameterColumn,
    { required, isMissing }: TableValidationState
): boolean => {
    if (isCellSubmittable(row[column.name], column)) return false;
    return !column.required || (required && isMissing);
};
