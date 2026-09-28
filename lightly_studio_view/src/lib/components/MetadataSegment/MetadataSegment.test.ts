import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import MetadataSegment from './MetadataSegment.svelte';

describe('MetadataSegment', () => {
    it('renders all categories initially and filters metadata by category selection', async () => {
        const { rerender } = render(MetadataSegment, {
            props: {
                metadata_dict: {
                    data: {
                        location: 'Basel',
                        weather: 'Sunny'
                    }
                }
            }
        });

        expect(screen.getByTestId('sample-metadata-metadata_location')).toHaveTextContent('Basel');
        expect(screen.getByTestId('sample-metadata-metadata_weather')).toHaveTextContent('Sunny');

        await fireEvent.click(screen.getByTestId('metadata-category-select'));
        await fireEvent.click(screen.getByRole('option', { name: 'weather' }));

        expect(screen.getByTestId('sample-metadata-metadata_location')).toBeVisible();
        expect(screen.queryByTestId('sample-metadata-metadata_weather')).toBeNull();

        await rerender({
            metadata_dict: {
                data: {
                    location: 'Bern',
                    weather: 'Rain',
                    season: 'Spring'
                }
            }
        });

        expect(screen.getByTestId('sample-metadata-metadata_location')).toHaveTextContent('Bern');
        expect(screen.queryByTestId('sample-metadata-metadata_weather')).toBeNull();
        expect(screen.getByTestId('sample-metadata-metadata_season')).toHaveTextContent('Spring');
    });
});
