
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="monostyle",
    version="0.0.1b0",
    author="Tobias Heinke",
    author_email="author@example.com",
    description="Linting framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tobiasHeinke/monostyle",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
