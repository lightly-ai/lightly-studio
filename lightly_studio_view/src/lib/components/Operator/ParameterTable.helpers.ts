import type { OperatorParameterColumn } from '$lib/hooks/useOperators/useOperators';
import { getCellConfig, isCellFilled, type ParameterTableRow } from './parameterTypeConfig';

/** Rows shown before the rows area starts scrolling instead of growing the dialog. */
export const MAX_VISIBLE_ROWS = 4;

// Inputs are h-10 (2.5rem) and rows are gap-2 (0.5rem) apart, so four rows measure
// 4 * 2.5rem + 3 * 0.5rem. Beyond that the rows area scrolls itself instead of pushing the dialog
// footer out of view.
export const MAX_ROWS_HEIGHT = 'max-h-[11.5rem]';

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

/**
 * Whether a cell should be flagged as invalid. Only the cells that actually block submission are
 * flagged, not every empty cell of the table.
 */
export const isCellInvalid = (
    row: ParameterTableRow,
    column: OperatorParameterColumn,
    { required, isMissing }: { required: boolean; isMissing: boolean }
): boolean => required && isMissing && column.required && !isCellFilled(row[column.name], column);
