import codecs
import os
from setuptools import setup, find_packages

with codecs.open("README.md", encoding="utf-8") as f:
    readme = f.read()


def get_version_file_path():
    github_actions_path = "/home/runner/work/gitlabform/gitlabform"
    if os.path.isfile(github_actions_path + "/version"):
        return github_actions_path + "/version"
    else:
        return "version"


setup(
    name="gitlabform",
    version=open(get_version_file_path()).read(),
    description="🏗 Specialized configuration as a code tool for GitLab projects, groups and more"
    " using hierarchical configuration written in YAML",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://gitlabform.github.io/gitlabform",
    author="Greg Dubicki and Contributors",
    keywords=["cli", "yaml", "gitlab", "configuration-as-code"],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Software Development :: Version Control :: Git",
    ],
    packages=find_packages(),
    package_data={"": ["LICENSE", "version", "*.md", "config.yml"]},
    include_package_data=True,
    python_requires=">=3.7.0",
    install_requires=[
        "certifi",  # we want the latest root certs for security
        "requests==2.28.2",
        "types-requests==2.28.11.17",
        "Jinja2==3.1.2",
        "MarkupSafe==2.1.2",
        "ruamel.yaml==0.17.21",
        "luddite==1.0.2",
        "cli-ui==0.17.2",
        "packaging==23.0",
        "mergedeep==1.3.4",
        "yamlpath==3.8.0",
        "ez-yaml==1.2.0",
    ],
    extras_require={
        "test": [
            "python-gitlab==3.13.0",
            "pytest==7.3.1",
            "xkcdpass==1.19.3",
            "pre-commit==2.21.0",  # not really for tests, but for development
            "coverage==7.2.1",
            "pytest-cov==4.0.0",
            "deepdiff==6.2.3",
            "pytest-rerunfailures==11.1.2",
            "cryptography==40.0.2",
            "mypy==1.1.1",
            "mypy-extensions==1.0.0",
        ],
        "docs": [
            "mkdocs",
            "mkdocs-material",
        ],
    },
    entry_points={
        "console_scripts": [
            "gitlabform=gitlabform.run:run",
        ],
    },
)
