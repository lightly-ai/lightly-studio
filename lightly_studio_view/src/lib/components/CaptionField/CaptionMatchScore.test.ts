import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import CaptionMatchScore from './CaptionMatchScore.svelte';
import { CAPTION_SEGMENT_MATCH_SCORE_KEY } from '$lib/constants';

describe('CaptionMatchScore', () => {
    it('renders the match score of the caption', () => {
        render(CaptionMatchScore, {
            props: {
                metadataDict: { data: { [CAPTION_SEGMENT_MATCH_SCORE_KEY]: 0.4567 } }
            }
        });

        expect(screen.getByTestId('caption-match-score')).toHaveTextContent('Match 0.457');
    });

    it('renders nothing without a match score', () => {
        render(CaptionMatchScore, {
            props: {
                metadataDict: { data: { other_key: 1 } }
            }
        });

        expect(screen.queryByTestId('caption-match-score')).not.toBeInTheDocument();
    });

    it('renders nothing without metadata', () => {
        render(CaptionMatchScore, { props: { metadataDict: null } });

        expect(screen.queryByTestId('caption-match-score')).not.toBeInTheDocument();
    });
});
