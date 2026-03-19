import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import VideoSampleMetadata from './VideoSampleMetadata.svelte';
import type { VideoView } from '$lib/api/lightly_studio_local';

describe('VideoSampleMetadata', () => {
    it('renders video metadata with all fields', () => {
        const video: VideoView = {
            file_name: 'test-video.mp4',
            file_path_abs: '/path/to/test-video.mp4',
            width: 1920,
            height: 1080,
            duration_s: 45.5,
            fps: 30.0
        } as VideoView;

        render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        expect(screen.getByText('test-video.mp4')).toBeInTheDocument();
        expect(screen.getByText('1920px')).toBeInTheDocument();
        expect(screen.getByText('1080px')).toBeInTheDocument();
        expect(screen.getByText('45.50 seconds')).toBeInTheDocument();
        expect(screen.getByText('30.00')).toBeInTheDocument();
    });

    it('renders Segment with correct title', () => {
        const video: VideoView = {
            file_name: 'test.mp4',
            file_path_abs: '/path/to/test.mp4',
            width: 640,
            height: 480,
            duration_s: 10.0,
            fps: 24.0
        } as VideoView;

        const { container } = render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        expect(container.textContent).toContain('Sample details');
    });

    it('renders file name with correct testid', () => {
        const video: VideoView = {
            file_name: 'my-video-file.mp4',
            file_path_abs: '/path/to/my-video-file.mp4',
            width: 1280,
            height: 720,
            duration_s: 60.0,
            fps: 25.0
        } as VideoView;

        render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        const fileNameElement = screen.getByTestId('video-file-name');
        expect(fileNameElement).toHaveTextContent('my-video-file.mp4');
    });

    it('renders width with correct testid', () => {
        const video: VideoView = {
            file_name: 'video.mp4',
            file_path_abs: '/path/to/video.mp4',
            width: 3840,
            height: 2160,
            duration_s: 120.0,
            fps: 60.0
        } as VideoView;

        render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        const widthElement = screen.getByTestId('video-width');
        expect(widthElement).toHaveTextContent('3840px');
    });

    it('renders height with correct testid', () => {
        const video: VideoView = {
            file_name: 'video.mp4',
            file_path_abs: '/path/to/video.mp4',
            width: 1920,
            height: 1440,
            duration_s: 30.0,
            fps: 30.0
        } as VideoView;

        render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        const heightElement = screen.getByTestId('video-height');
        expect(heightElement).toHaveTextContent('1440px');
    });

    it('formats duration to 2 decimal places', () => {
        const video: VideoView = {
            file_name: 'video.mp4',
            file_path_abs: '/path/to/video.mp4',
            width: 1920,
            height: 1080,
            duration_s: 123.456789,
            fps: 29.97
        } as VideoView;

        render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        expect(screen.getByText('123.46 seconds')).toBeInTheDocument();
    });

    it('formats fps to 2 decimal places', () => {
        const video: VideoView = {
            file_name: 'video.mp4',
            file_path_abs: '/path/to/video.mp4',
            width: 1920,
            height: 1080,
            duration_s: 60.0,
            fps: 29.970029
        } as VideoView;

        render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        expect(screen.getByText('29.97')).toBeInTheDocument();
    });

    it('displays all field labels correctly', () => {
        const video: VideoView = {
            file_name: 'test.mp4',
            file_path_abs: '/path/to/test.mp4',
            width: 1920,
            height: 1080,
            duration_s: 30.0,
            fps: 30.0
        } as VideoView;

        render(VideoSampleMetadata, {
            props: {
                video
            }
        });

        expect(screen.getByText('File Name:')).toBeInTheDocument();
        expect(screen.getByText('Width:')).toBeInTheDocument();
        expect(screen.getByText('Height:')).toBeInTheDocument();
        expect(screen.getByText('Duration:')).toBeInTheDocument();
        expect(screen.getByText('FPS:')).toBeInTheDocument();
    });
});
