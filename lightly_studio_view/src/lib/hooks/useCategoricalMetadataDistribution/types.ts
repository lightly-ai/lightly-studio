import type { CategoricalMetadataValue } from '$lib/services/types';

export type CategoricalMetadataBucket =
    | {
          id: string;
          kind: 'value';
          value: CategoricalMetadataValue;
          label: string;
          count: number;
      }
    | { id: string; kind: 'missing'; value: null; label: string; count: number }
    | { id: string; kind: 'other'; label: string; count: number };
