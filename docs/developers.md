# cli-eaa developer notes

## Versioning

When bumping to a new version 3 locations need update:

|File|Instructions|
|-|-|
|`/VERSION`|Replace the version number in the text file|
|`/cli-json`|In the `commands` > `version` key, update the value|
|`/libeaa/common.py`|Locate the `__version__` variable and update it|

## Visual Studio Code

There are some dependencies between python code sitting in `bin/` and `libeaa/` directories.
To avoid the Pylance warning, you may use the following settings in your `.vscode/settings.json`

```json
{
    "python.analysis.extraPaths": [
        "bin",
        "libeaa"
    ]
}
```