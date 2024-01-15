# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.2] - 2024-01-15
### :sparkles: New Features
- [`eba4b53`](https://github.com/kiyoon/jupynium.nvim/commit/eba4b5368349b1fa270ac38a7a28842d54c96f71) - add function for custom folds *(PR [#88](https://github.com/kiyoon/jupynium.nvim/pull/88) by [@fecet](https://github.com/fecet))*
- [`0acca13`](https://github.com/kiyoon/jupynium.nvim/commit/0acca13f90c92dfbbe4a45d34bc6d749c5c6ee82) - ruff linter, fix: ipynb2jupytext *(PR [#95](https://github.com/kiyoon/jupynium.nvim/pull/95) by [@kiyoon](https://github.com/kiyoon))*

### :bug: Bug Fixes
- [`5b794f8`](https://github.com/kiyoon/jupynium.nvim/commit/5b794f87610636ea50cf226235c00f2835fe632e) - large logs *(commit by [@kiyoon](https://github.com/kiyoon))*
- [`b02c65e`](https://github.com/kiyoon/jupynium.nvim/commit/b02c65e35c80ebeee4edb45897385857e4836625) - ruff target version py37 *(commit by [@kiyoon](https://github.com/kiyoon))*
- [`bebd597`](https://github.com/kiyoon/jupynium.nvim/commit/bebd59723869849a89976abda0655c6f4e858d65) - attach stderr to jupyter process *(commit by [@joh](https://github.com/joh))*
- [`5595ed8`](https://github.com/kiyoon/jupynium.nvim/commit/5595ed8ddf4cbdccf8ac139ead5e315cceeeedfc) - avoid attaching on_lines handler multiple times *(PR [#99](https://github.com/kiyoon/jupynium.nvim/pull/99) by [@joh](https://github.com/joh))*
  - :arrow_lower_right: *fixes issue [#92](undefined) opened by [@torifaye](https://github.com/torifaye)*
- [`c6fdf2f`](https://github.com/kiyoon/jupynium.nvim/commit/c6fdf2f38512d822d7444d58c1aa58703e004ee6) - use cache dir to store files over the package dir *(PR [#102](https://github.com/kiyoon/jupynium.nvim/pull/102) by [@kiyoon](https://github.com/kiyoon))*

### :zap: Performance Improvements
- [`05ef99a`](https://github.com/kiyoon/jupynium.nvim/commit/05ef99a10240377b2af7549cf8681f8e60bb469e) - cache `cells.line_types_entire_buf` to avoid repeated calls *(PR [#89](https://github.com/kiyoon/jupynium.nvim/pull/89) by [@kiyoon](https://github.com/kiyoon))*


[v0.2.2]: https://github.com/kiyoon/jupynium.nvim/compare/v0.2.1...v0.2.2