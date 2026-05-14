import { loadDimensionBounds } from './loadDimensionBounds';
import * as sdk from '$lib/api/lightly_studio_local/sdk.gen';
import { vi } from 'vitest';

type GetImageDimensionsReturn = Awaited<ReturnType<typeof sdk.getImageDimensions>>;

describe('loadDimensionBounds', () => {
    it('should return dimension bounds when loaded successfully', async () => {
        const mockData = {
            min_width: 100,
            max_width: 1920,
            min_height: 200,
            max_height: 1080
        };
        const mockedFn = vi
            .spyOn(sdk, 'getImageDimensions')
            .mockResolvedValue({ data: mockData, error: undefined } as GetImageDimensionsReturn);

        await expect(loadDimensionBounds({ collection_id: '1' })).resolves.toEqual({
            data: mockData,
            error: undefined
        });
        expect(mockedFn).toHaveBeenCalledWith({
            path: { collection_id: '1' },
            query: { annotation_label_ids: undefined }
        });
    });

    it('should include annotation ids in query when provided', async () => {
        const mockData = {
            min_width: 100,
            max_width: 1920,
            min_height: 200,
            max_height: 1080
        };
        const mockedFn = vi
            .spyOn(sdk, 'getImageDimensions')
            .mockResolvedValue({ data: mockData, error: undefined } as GetImageDimensionsReturn);

        await loadDimensionBounds({
            collection_id: '1',
            annotation_label_ids: ['mock_id_1', 'mock_id_2']
        });

        expect(mockedFn).toHaveBeenCalledWith({
            path: { collection_id: '1' },
            query: {
                annotation_label_ids: ['mock_id_1', 'mock_id_2']
            }
        });
    });

    it('should return an error when loading fails', async () => {
        vi.spyOn(sdk, 'getImageDimensions').mockResolvedValue({
            data: null,
            error: 'Not Found'
        } as unknown as GetImageDimensionsReturn);

        await expect(loadDimensionBounds({ collection_id: '1' })).resolves.toEqual({
            data: undefined,
            error: 'Error loading dimension bounds: Error: "Not Found"'
        });
    });

    it('should return an error when no data is returned', async () => {
        vi.spyOn(sdk, 'getImageDimensions').mockResolvedValue({
            data: null,
            error: undefined
        } as unknown as GetImageDimensionsReturn);

        await expect(loadDimensionBounds({ collection_id: '1' })).resolves.toEqual({
            data: undefined,
            error: 'Error loading dimension bounds: Error: No dimension bounds data'
        });
    });

    it('should return an error when promise is rejected', async () => {
        vi.spyOn(sdk, 'getImageDimensions').mockRejectedValue('oops');

        await expect(loadDimensionBounds({ collection_id: '1' })).resolves.toEqual({
            data: undefined,
            error: 'Error loading dimension bounds: oops'
        });
    });
});
