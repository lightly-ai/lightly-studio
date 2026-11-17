import type { ModelSuggestion } from './useModelSuggestionReview.svelte';

export const getModelSuggestionAppearance = (status: ModelSuggestion['status']) =>
    status === 'accepted'
        ? {
              colorStroke: '#60a5fa',
              colorFill: 'rgba(59, 130, 246, 0.35)',
              strokeDasharray: '',
              tagColor: '#1d4ed8'
          }
        : {
              colorStroke: '#fbbf24',
              colorFill: 'rgba(245, 158, 11, 0.35)',
              strokeDasharray: '6 5',
              tagColor: '#92400e'
          };
