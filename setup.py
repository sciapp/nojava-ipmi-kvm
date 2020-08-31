import os
import runpy
from setuptools import setup, find_packages


def get_version_from_pyfile(version_file="nojava_ipmi_kvm/_version.py"):
    file_globals = runpy.run_path(version_file)
    return file_globals["__version__"]


def get_long_description_from_readme(readme_filename="README.md"):
    long_description = None
    if os.path.isfile(readme_filename):
        with open(readme_filename, "r", encoding="utf-8") as readme_file:
            long_description = readme_file.read()
    return long_description


version = get_version_from_pyfile()
long_description = get_long_description_from_readme()

setup(
    name="nojava-ipmi-kvm",
    version=version,
    packages=find_packages(),
    python_requires="~=3.5",
    install_requires=["requests", "yacl", "pyyaml"],
    extras_require={"GUI": ["PyQt5>=5.12", "PyQtWebEngine>=5.12"]},
    entry_points={"console_scripts": ["nojava-ipmi-kvm = nojava_ipmi_kvm.cli:main"]},
    author="Ingo Meyer",
    author_email="i.meyer@fz-juelich.de",
    description="Access Java based ipmi kvm consoles without a local Java installation.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/sciapp/nojava-ipmi-kvm",
    keywords=["ipmi", "kvm", "vnc"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
)
