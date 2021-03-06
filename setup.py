#!/usr/bin/env python
"""
Setup file for Expyriment
"""


from __future__ import print_function
from builtins import *


__author__ = 'Florian Krause <florian@expyriment.org>, \
Oliver Lindemann <oliver@expyriment.org>'


import stat
import os
import sys
from subprocess import Popen, PIPE, call
try:
    from setuptools import setup
    from setuptools.command.sdist import sdist
    from setuptools.command.build_py import build_py
    from setuptools.command.install import install
    from setuptools.command.install_data import install_data
    from setuptools.command.bdist_wininst import bdist_wininst
except ImportError:
    from distutils.core import setup
    from distutils.command.sdist import sdist
    from distutils.command.build_py import build_py
    from distutils.command.install import install
    from distutils.command.install_data import install_data
    from distutils.command.bdist_wininst import bdist_wininst
from os import remove, close, chmod, path
from shutil import move, copyfile, copytree, rmtree
from tempfile import mkstemp
from glob import glob


# Settings
description='A Python library for cognitive and neuroscientific experiments'
author='Florian Krause, Oliver Lindemann'
author_email='florian@expyriment.org, oliver@expyriment.org'
license='GNU GPLv3'
url='http://www.expyriment.org'

package_dir={'expyriment': 'expyriment'}

packages = ['expyriment',
            'expyriment.control',
            'expyriment.io', 'expyriment.io.extras',
            'expyriment.io._parallelport',
            'expyriment.misc', 'expyriment.misc.extras',
            'expyriment.stimuli', 'expyriment.stimuli.extras',
            'expyriment.design', 'expyriment.design.extras']

package_data = {'expyriment': ['expyriment_logo.png', '_fonts/*.*']}

data_files = [('share/expyriment/documentation/api',
               glob('documentation/api/*.*')),
              ('share/expyriment/documentation/sphinx',
               glob('documentation/sphinx/*.*')),
              ('share/expyriment/documentation/sphinx',
               glob('documentation/sphinx/Makefile'))]

source_files = ['.release_info',
                'CHANGES.MD',
                'COPYING.txt',
                'Makefile',
                'README.md']

install_requires = ["future>=0.15,<1",
                    "pygame>=1.9,<2",
                    "pyopengl>=3.0,<4"]

extras_require = {
    'data_preprocessing': ["numpy>=1.6,<2"],
    'serialport':         ["pyserial>=3,<4"],
    'parallelport_linux': ["pyparallel>=0.2,<1"],
    'video':              ["sounddevice>=0.3,<1",
                           "mediadecoder>=0.1,<1"],
    'all':                ["numpy>=1.6,<2",
                           "pyserial>=3,<4",
                           "pyparallel>=0.2,<1",
                           "sounddevice>=0.3,<1",
                           "mediadecoder>=0.1,<1"],
    }


class Sdist(sdist):
    def get_file_list(self):
        version_nr, revision_nr, date = get_version_info_from_release_info()
        # If code is check out from GitHub repository, change .release_info
        if date.startswith("$Format:"):
            version_nr, revision_nr, date = get_version_info_from_git()
            version_nr = "tag: " + version_nr
            move(".release_info", ".release_info.bak")
            with open(".release_info", 'w') as f:
                f.write(u"{0}\n{1}\n{2}".format(version_nr, revision_nr, date))
        for f in source_files:
            self.filelist.append(f)
        sdist.get_file_list(self)

    def run(self):
        sdist.run(self)
        try:
            move(".release_info.bak", ".release_info")
        except:
            pass


# Manipulate the header of all files (only for building/installing from
# repository)
class Build(build_py):
    """Specialized Python source builder."""

    def byte_compile(self, files):
        for f in files:
            if f.endswith('.py'):
                # Create temp file
                fh, abs_path = mkstemp()
                new_file = open(abs_path, 'wb')
                old_file = open(f, 'rUb')
                for line in old_file:
                    if line[0:11] == '__version__':
                        new_file.write("__version__ = '" + version_nr + "'" +
                                       '\n')
                    elif line[0:12] == '__revision__':
                        new_file.write("__revision__ = '" + revision_nr + "'"
                                       + '\n')
                    elif line[0:8] == '__date__':
                        new_file.write("__date__ = '" + date + "'" + '\n')
                    else:
                        new_file.write(line)
                # Close temp file
                new_file.close()
                close(fh)
                old_file.close()
                # Remove original file
                remove(f)
                # Move new file
                move(abs_path, f)
                chmod(f,
                      stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        build_py.byte_compile(self, files)


# Clear old installation when installing
class Install(install):
    """Specialized installer."""

    def run(self):
        # Clear old installation
        try:
            olddir = path.abspath(self.install_lib + path.sep + "expyriment")
            oldegginfo = glob(path.abspath(self.install_lib) + path.sep +
                              "expyriment*.egg-info")
            for egginfo in oldegginfo:
                remove(egginfo)
            if path.isdir(olddir):
                rmtree(olddir)
        except:
            pass
        install.run(self)


# Clear old installation when installing (for bdist_wininst)
class Wininst(bdist_wininst):
    """Specialized installer."""

    def run(self):
        fh, abs_path = mkstemp(".py")
        new_file = open(abs_path, 'w')
        # Clear old installation
        new_file.write("""
from distutils import sysconfig
import os, shutil
old_installation = os.path.join(sysconfig.get_python_lib(), 'expyriment')
if os.path.isdir(old_installation):
    shutil.rmtree(old_installation)
""")
        new_file.close()
        close(fh)
        self.pre_install_script = abs_path
        bdist_wininst.run(self)


# Build Sphinx HTML documentation and add them to data_files
class InstallData(install_data):
    def run(self):
        
        # Try to build/add documentation
        try:
            cwd = os.getcwd()
            copytree('expyriment', 'documentation/sphinx/expyriment')
            os.chdir('documentation/sphinx/')
            call([sys.executable, "./create_rst_api_reference.py"])
            call(["sphinx-build", "-b", "html", "-d", "_build/doctrees", ".", "_build/html"])
            os.chdir(cwd)
            self.data_files.append(('share/expyriment/documentation/html',
                               glob('documentation/sphinx/_build/html/*.*')))
            self.data_files.append(('share/expyriment/documentation/html/_downloads',
                               glob('documentation/sphinx/_build/html/_downloads/*.*')))
            self.data_files.append(('share/expyriment/documentation/html/_images',
                               glob('documentation/sphinx/_build/html/_images/*.*')))
            self.data_files.append(('share/expyriment/documentation/html/_sources',
                               glob('documentation/sphinx/_build/html/_sources/*.*')))
            self.data_files.append(('share/expyriment/documentation/html/_static',
                               glob('documentation/sphinx/_build/html/_static/*.*')))
            self.data_files.append(('share/expyriment/documentation/html/_static/css',
                               glob('documentation/sphinx/_build/html/_static/css/*.*')))
            self.data_files.append(('share/expyriment/documentation/html/_static/fonts',
                               glob('documentation/sphinx/_build/html/_static/fonts/*.*')))
            self.data_files.append(('share/expyriment/documentation/html/_static/js',
                               glob('documentation/sphinx/_build/html/_static/js/*.*')))
        except:
            html_created = False
            warning = "HTML documentation NOT created! (sphinx and numpydoc installed?)"
            os.chdir(cwd)

        # Install data
        install_data.run(self)
        
        # Clean up Sphinx folder
        rmtree("documentation/sphinx/expyriment", ignore_errors=True)
        rmtree("documentation/sphinx/_build", ignore_errors=True)
        for file_ in glob("documentation/sphinx/expyriment.*"):
            remove_file(file_)
        remove_file("documentation/sphinx/Changelog.rst")
        remove_file("documentation/sphinx/CommandLineInterface.rst")
        remove_file("documentation/sphinx/sitemap.yml")


# Helper functions
def remove_file(file_):
    try:
        os.remove(file_)
    except:
        pass

def get_version_info_from_git():
    """Get version number, revision number and date from git repository."""

    proc = Popen(['git', 'describe', '--tags', '--dirty', '--always'], \
                        stdout=PIPE, stderr=PIPE)
    version_nr = "{0}".format(proc.stdout.read().lstrip(b"v").strip())
    proc = Popen(['git', 'log', '--format=%H', '-1'], \
                        stdout=PIPE, stderr=PIPE)
    revision_nr = proc.stdout.read().strip()[:7]
    proc = Popen(['git', 'log', '--format=%cd', '-1'],
                     stdout=PIPE, stderr=PIPE)
    date = proc.stdout.readline().strip()
    return version_nr, revision_nr, date

def get_version_info_from_release_info():
    """Get version number, revision number and date from .release_info."""

    with open(".release_info") as f:
        lines = []
        for line in f:
            lines.append(line)
    for x in lines[0].split(","):
        if "tag:" in x:
            version_nr = x.replace("tag:","").strip().lstrip(b"v")
        else:
            version_nr = ""
    revision_nr = lines[1].strip()[:7]
    date = lines[2].strip()
    # GitHub source archive (snapshot, no tag)
    if version_nr == "":
        with open("CHANGES.md") as f:
            for line in f:
                if line.lower().startswith("version"):
                    version_nr = "{0}-0-g{1}".format(line.split(" ")[1],
                                                    revision_nr)
                    break
    return version_nr, revision_nr, date

def get_version_info_from_file(filename):
    """Get version number, revision number and date from a .py file."""

    with open(filename) as f:
        for line in f:
            if line.startswith("__version__"):
                version_nr = line.split("'")[1]
            if line.startswith("__revision__"):
                revision_nr = line.split("'")[1]
            if line.startswith("__date__"):
                date = line.split("'")[1]
    return version_nr, revision_nr, date

def run():
    """Run the setup."""

    setup(name='expyriment',
          version=version_nr,
          description=description,
          author=author,
          author_email=author_email,
          license=license,
          url=url,
          packages=packages,
          package_dir=package_dir,
          package_data=package_data,
          data_files=data_files,
          install_requires=install_requires,
          extras_require=extras_require,
          cmdclass=cmdclass)


if __name__=="__main__":

    # Check if we are building/installing from built a archive/distribution
    version_nr, revision_nr, date = get_version_info_from_file("expyriment/__init__.py")
    if not version_nr == '':
        cmdclass={'install': Install, 
                  'bdist_wininst': Wininst,
                  'install_data': InstallData,}
        run()
        message = "from built archive/distribution"

    # If not, we are building/installing from source
    else:
        cmdclass={'sdist': Sdist,
                  'build_py': Build,
                  'install': Install,
                  'bdist_wininst': Wininst,
                  'install_data': InstallData}

        # Are we building/installing from a source archive/distribution?
        version_nr, revision_nr, date = get_version_info_from_release_info()
        if not date.startswith("$Format:"):
            run()
            message = "from source archive/distribution"

        # Are we building/installing from the GitHub repository?
        else:
            if True:
                proc = Popen(['git', 'rev-list', '--max-parents=0', 'HEAD'],
                             stdout=PIPE, stderr=PIPE)
                initial_revision = proc.stdout.readline()
                if not b'e21fa0b4c78d832f40cf1be1d725bebb2d1d8f10' in \
                                                                initial_revision:
                    raise Exception
                version_nr, revision_nr, date = get_version_info_from_git()
                run()
                message = "from repository"
            else:
                raise RuntimeError("Building/Installing Expyriment failed!")
   
    print("")
    print("Expyriment Version: [{0}] ({1})".format( version_nr, message))
    try:
        print("Warning:", warning)
    except:
        pass
