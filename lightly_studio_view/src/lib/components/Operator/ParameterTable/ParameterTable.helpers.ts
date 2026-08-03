import type { OperatorParameterColumn } from '$lib/hooks';
import { getCellConfig, isCellFilled, type ParameterTableRow } from '../parameterTypeConfig';

/** Rows shown before the rows area starts scrolling instead of growing the dialog. */
export const MAX_VISIBLE_ROWS = 4;

// Inputs are h-10 (2.5rem) and rows are gap-2 (0.5rem) apart, so four rows measure
// 4 * 2.5rem + 3 * 0.5rem = 11.5rem. The scroll container also holds the sticky header row
// (text-xs, 1rem line height) plus its gap and the p-2 padding, so it gets 11.5 + 1 + 0.5 + 1rem.
// Beyond that the rows area scrolls itself instead of pushing the dialog footer out of view.
export const MAX_ROWS_HEIGHT = 'max-h-[14rem]';

/** Tailwind cannot compile a class built at runtime, so the column count goes through style. */
export const buildGridStyle = (columnCount: number): string =>
    `grid-template-columns: repeat(${columnCount}, minmax(0, 1fr)) auto`;

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
 * Whether a cell holds a value the backend cannot accept. A numeric column reads `''` while its
 * input is empty or mid-edit, and the backend validates every cell against its column type
 * regardless of `required`, so such a cell is always invalid — not just on a required column.
 */
const isCellUnsubmittable = (row: ParameterTableRow, column: OperatorParameterColumn): boolean => {
    const { type } = getCellConfig(column);
    return (type === 'int' || type === 'float') && !isCellFilled(row[column.name], column);
};

/**
 * Whether a cell should be flagged as invalid. Cells that block submission are flagged: the empty
 * cells of required columns once the table is missing a value, and cells of any column whose value
 * the backend would reject outright.
 */
export const isCellInvalid = (
    row: ParameterTableRow,
    column: OperatorParameterColumn,
    { required, isMissing }: TableValidationState
): boolean =>
    isCellUnsubmittable(row, column) ||
    (required && isMissing && column.required && !isCellFilled(row[column.name], column));
