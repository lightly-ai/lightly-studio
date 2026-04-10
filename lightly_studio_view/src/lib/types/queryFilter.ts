/**
 * Canonical wire-format types for the dataset query builder.
 *
 * These types mirror the Python `MatchExpression` hierarchy in
 * `core/dataset_query/` and the Pydantic `WireExpression` model in
 * `core/dataset_query/wire.py`.
 *
 * Supported field names
 * ---------------------
 *   image.width, image.height, image.file_name, image.file_path_abs,
 *   image.created_at
 *   video.* — reserved for future support
 *
 * Supported ops for ordinal fields:   >, >=, <, <=, ==, !=
 * Supported ops for comparable fields (strings): ==, !=
 */

export type OrdinalOp = '>' | '>=' | '<' | '<=' | '==' | '!=';
export type ComparableOp = '==' | '!=';

export interface WireField {
    type: 'field';
    field: string;
    op: OrdinalOp;
    value: string | number;
}

export interface WireTagsContains {
    type: 'tags_contains';
    tag: string;
}

export interface WireAnd {
    type: 'and';
    terms: WireExpression[];
}

export interface WireOr {
    type: 'or';
    terms: WireExpression[];
}

/** Emitted by the Python API only — the frontend query builder does not produce this. */
export interface WireNot {
    type: 'not';
    term: WireExpression;
}

export type WireExpression = WireField | WireTagsContains | WireAnd | WireOr | WireNot;
