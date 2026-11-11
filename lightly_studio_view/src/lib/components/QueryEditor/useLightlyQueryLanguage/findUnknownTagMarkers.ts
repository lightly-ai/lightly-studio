import * as monaco from 'monaco-editor';
import { AstUtils } from 'langium';
import {
    isStringLiteral,
    isTagInExpression,
    type Query,
    type StringLiteral
} from '../language/generated/ast.js';

interface FindUnknownTagMarkersParams {
    query: Query;
    tagNames: ReadonlySet<string>;
}

/** Returns a warning marker for each `"name" IN tags` whose tag does not exist. */
export function findUnknownTagMarkers({
    query,
    tagNames
}: FindUnknownTagMarkersParams): monaco.editor.IMarkerData[] {
    return AstUtils.streamAllContents(query)
        .filter(isTagInExpression)
        .map((expression) => expression.tag_name)
        .filter(isStringLiteral)
        .filter((literal) => !tagNames.has(literal.value))
        .toArray()
        .flatMap(toMarker);
}

function toMarker(literal: StringLiteral): monaco.editor.IMarkerData[] {
    // Nodes created by parser error recovery can lack a source range.
    const range = literal.$cstNode?.range;
    if (!range) return [];
    return [
        {
            severity: monaco.MarkerSeverity.Warning,
            message: `Tag "${literal.value}" does not exist.`,
            // Langium ranges are 0-based; Monaco positions are 1-based.
            startLineNumber: range.start.line + 1,
            startColumn: range.start.character + 1,
            endLineNumber: range.end.line + 1,
            endColumn: range.end.character + 1
        }
    ];
}
