# cli-eaa MacOS installation notes

## Troubleshooting

### ERROR[0002] and externally-managed-environment error

If you are using multiple Python 11, the installation command `akamai install eaa`
might fail with the externally-managed-environment error (see [PEP 668](https://peps.python.org/pep-0668/)).

The error look like this:

```
% akamai install eaa
Attempting to fetch command from https://github.com/akamai/cli-eaa.git... [OK]
Installing... [====      ] ERROR[0002] unable to execute 'python3 -m pip install --user --no-cache --upgrade pip setuptools': error: externally-managed-environment

× This environment is externally managed
(...)
```

This is very common if you are using Homebrew and get a more recent Python version >= 11.

The workaround is to get back to the legacy behavior - and have PIP to discard the error.
You are gonna need a `pip.conf` file created in either of these file:

`$HOME/Library/Application Support/pip/pip.conf` if directory `$HOME/Library/Application Support/pip` exists else `$HOME/.config/pip/pip.conf`.

You might need to create the directory and the file, the minimal file should contain:

```
[global]
break-system-packages = true
```

Once created, you can run the `akamai install eaa` again and it should work.

See https://pip.pypa.io/en/stable/topics/configuration/