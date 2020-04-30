
from setuptools import setup, find_packages

import monostyle


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="monostyle",
    version=monostyle.__version__,
    license="GPLv3+"
    author="Tobias Heinke",
    author_email="tobias.heinke@outlook.com",
    description="A framework for style checking and linting",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=["linter", "rst", "documentation", "style guide"],
    url="https://github.com/tobiasHeinke/monostyle",
    download_url='https://pypi.org/project/monostyle/',
    project_urls={
        "Code": "https://github.com/tobiasHeinke/monostyle",
        "Issue tracker": "https://github.com/tobiasHeinke/monostyle/issues",
    },
    platforms="any",
    python_requires='>=3.6',
    zip_safe=False,
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={
        "": ["*.json", "*.txt"],
    },
    exclude_package_data={
        "": ["data/*.csv"],
    },
    entry_points={
        "console_scripts": [
            "monostyle = monostyle.__init__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta"
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Documentation",
        "Topic :: Software Development",
        "Topic :: Software Development :: Documentation",
        "Topic :: Text Processing",
        "Topic :: Text Processing :: Markup",
        "Topic :: Text Editors",
        "Topic :: Text Editors :: Documentation",
        "Topic :: Text Editors :: Text Processing",
    ],
)
