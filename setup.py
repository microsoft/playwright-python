# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="playwright",
    author="Microsoft Corporation",
    author_email="",
    description="A high-level API to automate web browsers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Microsoft/playwright-python",
    packages=["playwright"],
    include_package_data=True,
    install_requires=["greenlet", "pyee", "typing-extensions"],
    classifiers=[
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    use_scm_version={
        "version_scheme": "post-release",
        "write_to": "playwright/_repo_version.py",
        "write_to_template": 'version = "{version}"\n',
    },
    setup_requires=["setuptools_scm"],
)
