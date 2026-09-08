/**
 * UI-level types for the point-cloud labeling workspace shell.
 *
 * Kept separate from `./domain`, which models point-cloud data rather than chrome: the shell
 * takes its navigation context as plain values so it stays free of collection/transport concerns.
 */

/** One step of the source breadcrumb, e.g. dataset -> collection -> sample. */
export interface WorkspaceCrumb {
    /** Text shown for this step. */
    readonly label: string;
    /** Link target. The final (current) crumb has none. */
    readonly href?: string;
}
