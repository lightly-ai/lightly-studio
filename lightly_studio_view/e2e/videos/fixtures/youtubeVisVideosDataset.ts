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

    /** Total number of frames in the dataset */
    totalFrames: 50,

    /** Default page size when loading samples */
    defaultPageSize: 30,

    /** Labels actively used in tests with their sample/frame counts */
    labels: {
        airplane: {
            name: 'airplane',
            /** Total samples containing this label */
            sampleCount: 2,
            /** Total frames with this label */
            frameCount: 39,
            /** Position in alphabetically sorted label list */
            sortedIndex: 0
        },
        bird: {
            name: 'bird',
            sampleCount: 1,
            frameCount: 32,
            sortedIndex: 1
        },
        elephant: {
            name: 'elephant',
            sampleCount: 1,
            frameCount: 20,
            sortedIndex: 8
        }
    },
    airplaneVideo: {
        name: '00ad5016a4.mp4',
        width: 1280,
        height: 720
    }
} as const;
