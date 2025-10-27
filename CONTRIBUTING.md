# Contributing to LightlyStudio
### Welcome! We are glad that you want to contribute to our project!
We welcome contributions of all kinds, including:  
- Bug fixes  
- Documentation improvements (README, docs folder, examples)  
- New features

After you have your changes ready, and you create a new pull request, a maintainer will review your PR, may ask for changes, suggest improvements, or approve once ready.

## Development


```bash
git clone git@github.com:lightly-ai/lightly_studio.git
cd lightly_studio/lightly_studio
make start
```

This will:
- Install dependencies
- Build the application
- Start an example script

For starting it again, you can skip the build step by just calling `make start-example`.

To run static checks and unit tests use the following commands

```bash
cd lightly_studio/lightly_studio
make static-checks
make test
```

When updating the code please follow our coding guidelines for [backend](./docs/coding-guidelines/backend.md) and [frontend](./docs/coding-guidelines/frontend.md).

### Documentation

Documentation is in the [docs](./lightly_studio/docs) folder. To build the documentation, move to the [docs](./lightly_studio/docs) folder and run:

```
make docs
```
This builds the documentation in the [docs/site](./lightly_studio/docs/site) folder.


Docs can be served locally with:

```
make serve
```

#### Writing Documentation

The documentation source is in [docs/docs](./lightly_studio/docs/docs). The documentation is
written in Markdown (MyST flavor). For more information regarding formatting, see:

- https://pradyunsg.me/furo/reference/
- https://myst-parser.readthedocs.io/en/latest/syntax/typography.html

## SETTING UP YOUR ENVIRONMENT FOR DEVELOPMENT

### Requirements
- Python **3.8+**
- Node.js **22.11+**
- Access to **Google Cloud Platform** (request permission from @IgorSusmelj)

### Clone the Repositories

First, clone the example dataset repository. It provides a sample dataset used during development.

```bash
git clone https://github.com/lightly-ai/dataset_examples
```

### Defining Environment Variables

Request the `LIGHTLY_STUDIO_LICENSE_KEY` from a team developer and export it:

```shell
export LIGHTLY_STUDIO_LICENSE_KEY=<your_key_here>
```

Then, set the path to the example dataset, for example:

```shell
export DATASET_PATH=../../dataset_examples/coco_subset_128_images/images/
```

### Start the Backend

Inside the LightlyStudio repository, navigate to the `lightly_studio` directory and run:

```shell
make start
```

### Start the Frontend

In a new terminal tab, navigate to the `lightly_studio_view` directory and copy the environment file:

```shell
cp .env .env.local
```

Then, define the following variables in your `.env.local` file:

```
PUBLIC_SAMPLES_URL=http://localhost:8001/images
PUBLIC_LIGHTLY_STUDIO_API_URL=http://localhost:8001/
```

Finally, start the frontend:

```shell
npm run dev
```

### Exploring the Makefile

The `Makefile` includes several helpful commands. Here are some commonly used ones:

Run tests:

```shell
make test
```

Format code:

```shell
make format
```

You can explore more available commands directly in the `Makefile`.

### Contributor License Agreement (CLA)

To contribute to this repository, you must sign a Contributor License Agreement (CLA).
This is a one-time process done through GitHub when you open your first pull request.
You will be prompted automatically.

By signing the CLA, you agree that your contributions may be used under the terms of the project license.
