# Build (Windows)
```shell
py -m build
 ```

# Install (Windows)
```shell
 py -m pip install C:\<path>\actions-server\dist\actions_server-<version>-py3-none-any.whl --force-reinstall
```

# Upload test (Windows)
```shell
py -m twine upload --repository testpypi dist/*
```

# Upload prod (Windows)
```shell
py -m twine upload dist/*
```