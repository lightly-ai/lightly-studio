import { expect, type Locator, type Page } from '@playwright/test';

const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** The annotation tree in the filter panel of the Images and Annotations grids. */
export class AnnotationTree {
    constructor(public readonly page: Page) {}

    get root(): Locator {
        return this.page.getByTestId('annotation-tree');
    }

    getAllAnnotationsCheckbox(): Locator {
        return this.root.getByRole('checkbox', { name: 'All annotations', exact: true });
    }

    getSourceCheckbox(sourceName: string): Locator {
        return this.root.getByRole('checkbox', { name: sourceName, exact: true });
    }

    /** The class names. The Images grid must group "By class" first. */
    getClassGroupNames(): Locator {
        return this.root
            .getByTestId('annotation-tree-group-name')
            .filter({ hasNotText: 'No annotations' });
    }

    async groupByClass(): Promise<void> {
        const button = this.root.getByRole('button', { name: 'By class' });
        if ((await button.getAttribute('aria-pressed')) !== 'true') {
            await button.click();
        }
    }

    /**
     * Filters by a class like a selection list: the first class shows only that class, more
     * classes add to it, and unticking the last class shows all annotations again.
     */
    async toggleClass(className: string): Promise<void> {
        await expect(this.root).toBeVisible();
        // The flat list of the Annotations grid has no "By class" switch.
        const isFlat = (await this.root.getByRole('button', { name: 'By class' }).count()) === 0;
        if (!isFlat) {
            await this.groupByClass();
        }
        const name = escapeRegExp(className);
        const checkbox = isFlat
            ? this.root.getByRole('checkbox', { name: new RegExp(`^${name} in `) })
            : this.root.getByRole('checkbox', { name: className, exact: true });
        const onlyButton = isFlat
            ? this.root.getByRole('button', { name: new RegExp(`^Only ${name} in `) })
            : this.root.getByRole('button', { name: `Only ${className}`, exact: true });
        await expect(checkbox).toBeVisible();

        if ((await this.getAllAnnotationsCheckbox().getAttribute('aria-checked')) === 'true') {
            // "Only" shows on hover.
            await checkbox.hover();
            await onlyButton.click();
            return;
        }
        const wasTicked = (await checkbox.getAttribute('aria-checked')) === 'true';
        await checkbox.click();
        if (
            wasTicked &&
            (await this.getAllAnnotationsCheckbox().getAttribute('aria-checked')) === 'false'
        ) {
            await this.getAllAnnotationsCheckbox().click();
        }
    }
}
