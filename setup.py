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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
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
    python_requires=">=3.8.0",
    install_requires=[
        "certifi",  # we want the latest root certs for security
        "cli-ui==0.17.2",
        "ez-yaml==1.2.0",
        "Jinja2==3.1.3",
        "luddite==1.0.2",
        "MarkupSafe==2.1.5",
        "mergedeep==1.3.4",
        "packaging==23.2",
        "python-gitlab==4.4.0",
        "requests==2.31.0",
        "ruamel.yaml==0.17.21",
        "types-requests==2.31.0.20240218",
        "yamlpath==3.8.2",
    ],
    extras_require={
        "test": [
            "coverage==7.4.3",
            "cryptography==42.0.5",
            "deepdiff==6.7.1",
            "mypy==1.8.0",
            "mypy-extensions==1.0.0",
            "pre-commit==2.21.0",  # not really for tests, but for development
            "pytest==8.0.2",
            "pytest-cov==4.1.0",
            "pytest-rerunfailures==13.0",
            "xkcdpass==1.19.8",
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
