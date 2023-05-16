import io
import os
import platform
import subprocess
import sys
from shutil import rmtree

from setuptools import Command, setup
from setuptools.command.install import install

platform_commands = {
    'Linux': {
        'command': ['sudo', 'apt-get', 'install', '-y', 'libmagic1'],
        'message': 'Failed to install libmagic1. Please install it manually with command: sudo apt-get install libmagic1',
    },
    'Windows': {
        'command': ['pip', 'install', 'python-magic-bin'],
        'message': 'Failed to install python-magic-bin. Please install it manually with command: pip install python-magic-bin',
    },
    'Darwin': {
        'command': ['brew', 'install', 'libmagic'],
        'message': 'Failed to install libmagic. Please install it manually with command: brew install libmagic',
    },
}


class PostInstallCommand(install):
    def run(self):
        install.run(self)

        try:
            current_system = platform.system()

            if current_system in platform_commands:
                command_info = platform_commands[current_system]
                try:
                    subprocess.run(command_info['command'], check=True)
                except subprocess.CalledProcessError:
                    print(command_info['message'])

        except:
            pass


# Package meta-data.
NAME = "scrapy_arweave"
DESCRIPTION = "Scrapy is a popular open-source and collaborative python framework for extracting the data you need from websites. scrapy-arweave provides scrapy pipelines and feed exports to store items into Arweave."
URL = "https://github.com/pawanpaudel93/scrapy-arweave"
EMAIL = "pawanpaudel93@gmail.com"
AUTHOR = "Pawan Paudel"
REQUIRES_PYTHON = ">=3.0"
VERSION = "0.0.1"

REQUIRED = [
    "python-magic",
    "pyarweave",
]

EXTRAS = {
    # 'fancy feature': ['django'],
}

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    project_slug = NAME.lower().replace("-", "_").replace(" ", "_")
    with open(os.path.join(here, project_slug, "__version__.py")) as f:
        exec(f.read(), about)
else:
    about["__version__"] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(about["__version__"]))
        os.system("git push --tags")

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    py_modules=["scrapy_arweave"],
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    packages=["scrapy_arweave"],
    include_package_data=True,
    license="ISC",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    # $ setup.py publish support.
    cmdclass={"upload": UploadCommand, "install": PostInstallCommand},
)
