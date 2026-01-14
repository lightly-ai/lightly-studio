/**
 * Youtube Vis 50 Videos Dataset Test Fixture
 *
 * This fixture defines the expected properties of the youtube_vis_50_videos dataset
 * used in E2E tests. Only includes labels and values actively used in tests.
 *
 * Note: These values are based on the actual youtube_vis_50_videos dataset in
 * lightly_studio/datasets/youtube_vis_50_videos/ and should match reality.
 */

/**
 * dataset-level constants
 */
export const youtubeVisVideosDataset = {
    /** Total number of samples in the dataset */
    totalSamples: 50,

    /** Default page size when loading samples */
    defaultPageSize: 30
} as const;
