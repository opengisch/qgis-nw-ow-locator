# NW OW Locator – QGIS Plugin

Locator integration for searching the geodata infrastructure of the cantons Obwalden and Nidwalden.
This plugin can be used to search for layers, addresses and other objects in NW and OW.



## Development


[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![flake8](https://img.shields.io/badge/linter-flake8-green)](https://flake8.pycqa.org/)


### Tooling

This project is configured with the following tools:

- [Black](https://black.readthedocs.io/en/stable/) to format the code without any existential question
- [iSort](https://pycqa.github.io/isort/) to sort the Python imports

Code rules are enforced with [pre-commit](https://pre-commit.com/) hooks.  
Static code analysis is based on: Flake8.

### CI/CD

If you mean to deploy it to the [official QGIS plugins repository](https://plugins.qgis.org/), remember to set your OSGeo credentials (`OSGEO_USER_NAME` and `OSGEO_USER_PASSWORD`) as environment variables in your CI/CD tool.

### Translation
To collect all strings that need to be translated in the code base, e.g. `self.tr(string)`, use the `pylupdate5` command:
```shell
pylupdate5 -noobsolete nw_ow_locator/i18n/nw_ow_locator.pro
```
- `-noobsolete` will remove all obsolete strings from the translation files.
- Make sure to add new python files with translateable strings to the `i18n/nw_ow_locator.pro` file in section `SOURCES =`.

The generated *.ts files can be found in the `nw_ow_locator/i18n` folder and manually translated.

To generate the binary translation files (*.qm), use the `lrelease` command:

```shell
lrelease nw_ow_locator/i18n/nw_ow_locator_de.ts nw_ow_locator/i18n/nw_ow_locator_en.ts
```


For a more streamlined translation process as part of the CI/CD on GitHub,
use the qgis-plugin-ci package in combination with the online translation app [transifex](https://www.transifex.com/).

More details can be found in the qgis-plugin-ci documentation [here](https://opengisch.github.io/qgis-plugin-ci/usage/cli_translation.html).
For a live example, see the SwissLocator plugin release actions on [GitHub](https://github.com/opengisch/qgis-swiss-locator/blob/master/.github/workflows/plugin-package.yml#L41).


## License

Distributed under the terms of the [`GPLv3` license](LICENSE).
