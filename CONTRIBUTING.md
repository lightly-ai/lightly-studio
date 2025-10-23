# Contributing to LightlyStudio

## Development


```bash
git clone git@github.com:lightly-ai/project-purple.git
cd lightly_studio
cd lightly_studio
make start
```

This will:
- Install dependencies
- Build the application
- Start an example script

For starting it again, you can skip the build step by just calling `make start-example`.

To run static checks and unit tests use the following commands

```bash
make static-checks
make test
```
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

### Contributor License Agreement (CLA)

To contribute to this repository, you must sign a Contributor License Agreement (CLA).
This is a one-time process done through GitHub when you open your first pull request.
You will be prompted automatically.

By signing the CLA, you agree that your contributions may be used under the terms of the project license.
