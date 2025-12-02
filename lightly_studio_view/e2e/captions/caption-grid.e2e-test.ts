import { test, expect } from '../utils';

test.beforeEach(async ({ captionsPage }) => {
    await captionsPage.goto();
});

test('dummy captions test', async () => {
    // TODO(Michal, 12/2025): Implement caption grid tests.
    expect(true).toBe(true);
});
