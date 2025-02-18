# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.6] - 2025-02-18
### :boom: BREAKING CHANGES
- due to [`af57c1b`](https://github.com/kiyoon/jupynium.nvim/commit/af57c1bb314e024aba7806653cf728e8558f0d4d) - drop python 3.8, simplify dep, fix ruff *(commit by [@kiyoon](https://github.com/kiyoon))*:

  drop python 3.8, simplify dep, fix ruff


### :bug: Bug Fixes
- [`b0b7157`](https://github.com/kiyoon/jupynium.nvim/commit/b0b71577c6e4a613b6a4180068dd0b2de0659e52) - **treesitter**: markdown injection *(commit by [@kiyoon](https://github.com/kiyoon))*
- [`22fdc6c`](https://github.com/kiyoon/jupynium.nvim/commit/22fdc6c1161abe4e46de083aa0702f90970258a9) - JupyniumLoadFromIpynbTabAndSync *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.2.5] - 2024-11-14
### :sparkles: New Features
- [`828052e`](https://github.com/kiyoon/jupynium.nvim/commit/828052ece86a5470f97247f6621e8a577154ee41) - code cell # %% with additional comments *(PR [#127](https://github.com/kiyoon/jupynium.nvim/pull/127) by [@ESSO0428](https://github.com/ESSO0428))*

### :recycle: Refactors
- [`1e57296`](https://github.com/kiyoon/jupynium.nvim/commit/1e572965813719c9ef123f777d79814e91d1a2cf) - add Config and UserConfig types *(commit by [@kiyoon](https://github.com/kiyoon))*


## [v0.2.4] - 2024-06-17
### :boom: BREAKING CHANGES
- due to [`d83c56a`](https://github.com/kiyoon/jupynium.nvim/commit/d83c56a9c886ded0b1ff6fe1e5a39512d7a06901) - drop python3.7, remove deprecated markdown cell syntax, hide migration guide banner *(PR [#119](https://github.com/kiyoon/jupynium.nvim/pull/119) by [@kiyoon](https://github.com/kiyoon))*:

  drop python3.7, remove deprecated markdown cell syntax, hide migration guide banner (#119)

- due to [`e730e34`](https://github.com/kiyoon/jupynium.nvim/commit/e730e34fce0015f6227dfa77cf48c525cca366a2) - remove deprecated markdown syntax *(PR [#121](https://github.com/kiyoon/jupynium.nvim/pull/121) by [@kiyoon](https://github.com/kiyoon))*:

  remove deprecated markdown syntax (#121)

- due to [`369b58f`](https://github.com/kiyoon/jupynium.nvim/commit/369b58fca4af3718f8312cb10988b3fdc2892b4f) - remove deprecated commands *(PR [#122](https://github.com/kiyoon/jupynium.nvim/pull/122) by [@kiyoon](https://github.com/kiyoon))*:

  remove deprecated commands (#122)


### :sparkles: New Features
- [`a43308c`](https://github.com/kiyoon/jupynium.nvim/commit/a43308c2929479e1fc18be9cd991fc4a5a566ad9) - ignore notifications *(PR [#120](https://github.com/kiyoon/jupynium.nvim/pull/120) by [@kiyoon](https://github.com/kiyoon))*
  - :arrow_lower_right: *addresses issue [#118](https://github.com/kiyoon/jupynium.nvim/issues/118) opened by [@singledoggy](https://github.com/singledoggy)*
- [`dbb9dff`](https://github.com/kiyoon/jupynium.nvim/commit/dbb9dffb6d1f5502c4caa028fe3571eccd5a2403) - nvim-notify better view with conceallevel=2 *(commit by [@kiyoon](https://github.com/kiyoon))*
- [`69ec5de`](https://github.com/kiyoon/jupynium.nvim/commit/69ec5dea0ac96b3719db69f82a1167ee328cc5ce) - notify better conceal *(commit by [@kiyoon](https://github.com/kiyoon))*

### :bug: Bug Fixes
- [`a0cfec0`](https://github.com/kiyoon/jupynium.nvim/commit/a0cfec051f47b72f4501970e5103120dd71891c2) - download_ipynb exception *(PR [#115](https://github.com/kiyoon/jupynium.nvim/pull/115) by [@kiyoon](https://github.com/kiyoon))*
  - :arrow_lower_right: *fixes issue [#114](https://github.com/kiyoon/jupynium.nvim/issues/114) opened by [@githubjacky](https://github.com/githubjacky)*
- [`46cf521`](https://github.com/kiyoon/jupynium.nvim/commit/46cf521f408e2e7783e8526b606e0bf1bf78e659) - start sync hanging *(commit by [@kiyoon](https://github.com/kiyoon))*
- [`6cf5b66`](https://github.com/kiyoon/jupynium.nvim/commit/6cf5b66fa7d73673af11fb8dc6305cec1e1d1cc3) - broken autodownload and autoscroll toggle commands *(commit by [@kiyoon](https://github.com/kiyoon))*
- [`06f66f2`](https://github.com/kiyoon/jupynium.nvim/commit/06f66f25e9db861e7774657e2c55ac70fb1fba7c) - error in empty ipynb and default kernel not existing *(PR [#124](https://github.com/kiyoon/jupynium.nvim/pull/124) by [@kiyoon](https://github.com/kiyoon))*
  - :arrow_lower_right: *fixes issue [#123](https://github.com/kiyoon/jupynium.nvim/issues/123) opened by [@1nuno](https://github.com/1nuno)*

### :recycle: Refactors
- [`e730e34`](https://github.com/kiyoon/jupynium.nvim/commit/e730e34fce0015f6227dfa77cf48c525cca366a2) - remove deprecated markdown syntax *(PR [#121](https://github.com/kiyoon/jupynium.nvim/pull/121) by [@kiyoon](https://github.com/kiyoon))*
- [`369b58f`](https://github.com/kiyoon/jupynium.nvim/commit/369b58fca4af3718f8312cb10988b3fdc2892b4f) - remove deprecated commands *(PR [#122](https://github.com/kiyoon/jupynium.nvim/pull/122) by [@kiyoon](https://github.com/kiyoon))*


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
[v0.2.3]: https://github.com/kiyoon/jupynium.nvim/compare/v0.2.2...v0.2.3
[v0.2.4]: https://github.com/kiyoon/jupynium.nvim/compare/v0.2.2...v0.2.4
[v0.2.5]: https://github.com/kiyoon/jupynium.nvim/compare/v0.2.4...v0.2.5
[v0.2.6]: https://github.com/kiyoon/jupynium.nvim/compare/v0.2.5...v0.2.6
