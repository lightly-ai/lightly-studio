import type { FilterOption } from './buildOptions';

export function getCheckboxLabel(option: FilterOption, label: string): string {
    return `${
        option.bucket.kind === 'missing' ? 'Select missing metadata' : `Select value ${label}`
    }, ${option.retained ? 'count unavailable' : `${option.bucket.count} ${option.bucket.count === 1 ? 'sample' : 'samples'}`}`;
}
