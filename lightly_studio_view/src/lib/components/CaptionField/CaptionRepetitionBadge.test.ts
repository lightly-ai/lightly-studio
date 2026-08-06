import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import {
    REPEATED_CAPTION_GROUP_ID_KEY,
    REPEATED_CAPTION_MAX_SIMILARITY_KEY
} from '$lib/constants';
import CaptionRepetitionBadge from './CaptionRepetitionBadge.svelte';

describe('CaptionRepetitionBadge', () => {
    it('renders group id and max similarity', () => {
        render(CaptionRepetitionBadge, {
            props: {
                metadataDict: {
                    data: {
                        [REPEATED_CAPTION_GROUP_ID_KEY]: 1,
                        [REPEATED_CAPTION_MAX_SIMILARITY_KEY]: 0.9123
                    }
                }
            }
        });

        expect(screen.getByTestId('caption-repeat-group')).toHaveTextContent('Repeat G1');
        expect(screen.getByTestId('caption-repeat-group')).toHaveAttribute(
            'data-repeat-group',
            '1'
        );
        expect(screen.getByTestId('caption-repeat-group-dot')).toBeInTheDocument();
        expect(screen.getByTestId('caption-repeat-max-sim')).toHaveTextContent('Max sim 0.912');
    });

    it('renders nothing without repetition metadata', () => {
        render(CaptionRepetitionBadge, {
            props: { metadataDict: { data: { other_key: 1 } } }
        });

        expect(screen.queryByTestId('caption-repetition-meta')).not.toBeInTheDocument();
    });
});
