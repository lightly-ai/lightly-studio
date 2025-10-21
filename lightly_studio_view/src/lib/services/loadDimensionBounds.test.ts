import { loadDimensionBounds } from './loadDimensionBounds';
import * as datasetClient from './dataset';
import { vi } from 'vitest';

type GetReturnType = Awaited<ReturnType<typeof datasetClient.default.GET>>;

describe('loadDimensionBounds', () => {
    it('should return dimension bounds when loaded successfully', async () => {
        const mockData = {
            min_width: 100,
            max_width: 1920,
            min_height: 200,
            max_height: 1080
        };
        const mockedClient = vi
            .spyOn(datasetClient.default, 'GET')
            .mockResolvedValue({ data: mockData, error: undefined } as unknown as GetReturnType);

        await expect(loadDimensionBounds({ dataset_id: '1' })).resolves.toEqual({
            data: mockData,
            error: undefined
        });
        expect(mockedClient).toHaveBeenCalledWith('/api/datasets/{dataset_id}/samples/dimensions', {
            params: {
                path: { dataset_id: '1' },
                query: {}
            }
        });
    });

    it('should include annotation ids in query when provided', async () => {
        const mockData = {
            min_width: 100,
            max_width: 1920,
            min_height: 200,
            max_height: 1080
        };
        const mockedClient = vi
            .spyOn(datasetClient.default, 'GET')
            .mockResolvedValue({ data: mockData, error: undefined } as unknown as GetReturnType);

        await loadDimensionBounds({
            dataset_id: '1',
            annotation_label_ids: ['mock_id_1', 'mock_id_2']
        });

        expect(mockedClient).toHaveBeenCalledWith('/api/datasets/{dataset_id}/samples/dimensions', {
            params: {
                path: { dataset_id: '1' },
                query: {
                    annotation_label_ids: ['mock_id_1', 'mock_id_2']
                }
            }
        });
    });

    it('should return an error when loading fails', async () => {
        vi.spyOn(datasetClient.default, 'GET').mockResolvedValue({
            data: null,
            error: 'Not Found'
        } as unknown as GetReturnType);

        await expect(loadDimensionBounds({ dataset_id: '1' })).resolves.toEqual({
            data: undefined,
            error: 'Error loading dimension bounds: Error: "Not Found"'
        });
    });

    it('should return an error when no data is returned', async () => {
        vi.spyOn(datasetClient.default, 'GET').mockResolvedValue({
            data: null,
            error: undefined
        } as unknown as GetReturnType);

        await expect(loadDimensionBounds({ dataset_id: '1' })).resolves.toEqual({
            data: undefined,
            error: 'Error loading dimension bounds: Error: No dimension bounds data'
        });
    });

    it('should return an error when promise is rejected', async () => {
        vi.spyOn(datasetClient.default, 'GET').mockRejectedValue('oops');

        await expect(loadDimensionBounds({ dataset_id: '1' })).resolves.toEqual({
            data: undefined,
            error: 'Error loading dimension bounds: oops'
        });
    });
});
