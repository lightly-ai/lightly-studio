import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import '@testing-library/jest-dom';
import { useTileFields } from '$lib/hooks/useTileFields/useTileFields';
import TileFieldsMenu from './TileFieldsMenu.svelte';

describe('TileFieldsMenu', () => {
    it('offers image fields and metadata, and ticks a field for the collection', async () => {
        render(TileFieldsMenu, {
            props: { collectionId: 'images-1', isAnnotations: false, metadataKeys: ['location'] }
        });

        await fireEvent.click(screen.getByTestId('tile-fields-trigger'));

        expect(screen.getByText('Annotation classes')).toBeInTheDocument();
        expect(screen.queryByText('Annotation source')).not.toBeInTheDocument();
        await fireEvent.click(screen.getByText('location'));

        expect(get(useTileFields().tileFields)['images-1']).toEqual(['metadata:location']);
        expect(screen.getByTestId('tile-fields-trigger')).toHaveTextContent('Show on tiles (1)');
    });

    it('offers the annotation source on the annotations grid', async () => {
        render(TileFieldsMenu, {
            props: { collectionId: 'annotations-1', isAnnotations: true, metadataKeys: [] }
        });

        await fireEvent.click(screen.getByTestId('tile-fields-trigger'));

        expect(screen.getByText('Annotation class')).toBeInTheDocument();
        expect(screen.getByText('Annotation source')).toBeInTheDocument();
        expect(screen.queryByText('Metadata')).not.toBeInTheDocument();
    });

    it('filters single tags and sources by the search and ticks one', async () => {
        render(TileFieldsMenu, {
            props: {
                collectionId: 'images-2',
                isAnnotations: false,
                metadataKeys: ['location'],
                tags: [
                    { tag_id: 't1', name: 'train' },
                    { tag_id: 't2', name: 'val' }
                ],
                sources: [{ id: 's1', name: 'model_v1' }]
            }
        });

        await fireEvent.click(screen.getByTestId('tile-fields-trigger'));
        await fireEvent.input(screen.getByLabelText('Search fields'), {
            target: { value: 'TRA' }
        });

        expect(screen.getByText('train')).toBeInTheDocument();
        expect(screen.queryByText('val')).not.toBeInTheDocument();
        expect(screen.queryByText('model_v1')).not.toBeInTheDocument();
        expect(screen.queryByText('Fields')).not.toBeInTheDocument();
        await fireEvent.click(screen.getByText('train'));
        expect(get(useTileFields().tileFields)['images-2']).toEqual(['tag:t1']);

        await fireEvent.input(screen.getByLabelText('Search fields'), {
            target: { value: 'zebra' }
        });
        expect(screen.getByText('No matching fields')).toBeInTheDocument();
    });
});
