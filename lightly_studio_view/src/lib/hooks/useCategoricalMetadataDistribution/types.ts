export type CategoricalMetadataBucket =
    | {
          id: string;
          kind: 'value';
          value: string | boolean;
          label: string;
          count: number;
      }
    | { id: string; kind: 'missing'; value: null; label: string; count: number }
    | { id: string; kind: 'other'; label: string; count: number };
