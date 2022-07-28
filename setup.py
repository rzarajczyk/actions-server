import os

import setuptools
import time

with open("README.md", "r") as fh:
    long_description = fh.read()

postfix = "" if os.getenv("RELEASE", "0") == "1" else ".dev%s" % round(time.time())

setuptools.setup(
    name="actions-server",
    version="0.0.9%s" % postfix,
    description="A very simple, multi-threaded HTTP server",
    author="Rafał Zarajczyk",
    author_email="rzarajczyk@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rzarajczyk/actions-server",
    keywords=["HTTP", "SERVER"],
    packages=['actions_server'],
    package_dir={'actions_server': './src/actions_server'},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=["requests>=2.27.1", "multipart>=0.2.4"],
)
