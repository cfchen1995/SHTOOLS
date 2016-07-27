#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import as _absolute_import
from __future__ import division as _division
from __future__ import print_function as _print_function
import os
import re
import sys
import sysconfig

from numpy.distutils.core import setup
from numpy.distutils.command.build import build
from numpy.distutils.fcompiler import FCompiler, get_default_fcompiler
from numpy.distutils.misc_util import Configuration
from subprocess import CalledProcessError, check_output, check_call


def get_version():
    """Get version from git and VERSION file

    Derived from: https://github.com/Changaco/version.py
    """
    d = os.path.dirname(__file__)
    # get release number from VERSION
    with open(os.path.join(d, 'VERSION')) as f:
        vre = re.compile('.Version: (.+)$', re.M)
        version = vre.search(f.read()).group(1)

    if os.path.isdir(os.path.join(d, '.git')):
        # Get the version using "git describe".
        cmd = 'git describe --tags'
        try:
            git_version = check_output(cmd.split()).decode().strip()[1:]
        except CalledProcessError:
            raise RuntimeError('Unable to get version number from git tags')

        # PEP440 compatibility
        if '-' in git_version:
            # increase version by 0.1 if any new revision exists in repo
            version = '{:.1f}'.format(float(version) + 0.1)
            git_revision = check_output(['git', 'rev-parse', 'HEAD'])
            git_revision = git_revision.strip().decode('ascii')
            version += '.dev0+' + git_revision[:7]

    return version


# Custom Builder
class SHTOOLS_build(build):
    """This overrides the standard build class to include the doc build."""

    description = "builds python documentation"

    def run(self):
        """Build the Fortran library, all python extensions and the docs."""
        # build Fortran library using the makefile
        print('---- BUILDING ----')
        build.run(self)

        # build documentation
        print('---- BUILDING DOCS ----')
        docdir = os.path.join(self.build_lib, 'pyshtools', 'doc')
        self.mkpath(docdir)
        doc_builder = os.path.join(self.build_lib, 'pyshtools', 'make_docs.py')
        doc_source = '.'
        check_call(['python', doc_builder, doc_source, self.build_lib])

        print('---- ALL DONE ----')


CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Fortran',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Topic :: Scientific/Engineering',
    'Topic :: Scientific/Engineering :: GIS',
    'Topic :: Scientific/Engineering :: Mathematics',
    'Topic :: Scientific/Engineering :: Physics'
]


KEYWORDS = ['Spherical Harmonics', 'Wigner Symbols']


INSTALL_REQUIRES = [
    'future>=0.12.4',
    'numpy>=1.0.0']

# configure python extension to be compiled with f2py


def get_compiler_flags():
    """Set fortran flags depending on the compiler."""
    compiler = get_default_fcompiler()
    if compiler == 'absoft':
        flags = ['-m64', '-O3', '-YEXT_NAMES=LCS', '-YEXT_SFX=_',
                 '-fpic', '-speed_math=10']
    elif compiler == 'gnu95':
        flags = ['-m64', '-fPIC', '-O3', '-ffast-math']
    elif compiler == 'intel':
        flags = ['-m64', '-free', '-O3', '-Tf']
    elif compiler == 'g95':
        flags = ['-O3', '-fno-second-underscore']
    elif compiler == 'pg':
        flags = ['-fast']
    else:
        flags = ['-m64', '-O3']
    return flags


def configuration(parent_package='', top_path=None):
    """Configure all packages that need to be built."""
    config = Configuration('', parent_package, top_path)

    F95FLAGS = get_compiler_flags()

    kwargs = {}
    kwargs['extra_compile_args'] = F95FLAGS
    kwargs['f2py_options'] = ['--quiet']

    # numpy.distutils.fcompiler.FCompiler doesn't support .F95 extension
    compiler = FCompiler(get_default_fcompiler())
    compiler.src_extensions.append('.F95')
    compiler.language_map['.F95'] = 'f90'

    # collect all Fortran sources
    files = os.listdir('src')
    exclude_sources = ['PlanetsConstants.f95', 'PythonWrapper.f95']
    sources = [os.path.join('src', file) for file in files if
               file.lower().endswith('.f95') and file not in exclude_sources]

    # (from http://stackoverflow.com/questions/14320220/
    #              testing-python-c-libraries-get-build-path)):
    build_lib_dir = "{dirname}.{platform}-{version[0]}.{version[1]}"
    dirparams = {'dirname': 'temp',
                 'platform': sysconfig.get_platform(),
                 'version': sys.version_info}
    libdir = os.path.join('build', build_lib_dir.format(**dirparams))
    print('searching SHTOOLS in:', libdir)

    # Fortran compilation
    config.add_library('SHTOOLS',
                       sources=sources,
                       **kwargs)

    # SHTOOLS
    config.add_extension('pyshtools._SHTOOLS',
                         include_dirs=[libdir],
                         library_dirs=[libdir],
                         libraries=['SHTOOLS', 'fftw3', 'm', 'lapack', 'blas'],
                         sources=['src/pyshtools.pyf', 'src/PythonWrapper.f95'],
                         **kwargs)

    # constants
    config.add_extension('pyshtools._constant',
                         sources=['src/PlanetsConstants.f95'],
                         **kwargs)

    return config


metadata = dict(
    name='pyshtools',
    version=get_version(),
    description='SHTOOLS - Tools for working with spherical harmonics',
    url='http://shtools.ipgp.fr',
    download_url='https://github.com/SHTOOLS/SHTOOLS/zipball/master',
    author='Mark Wieczorek, Matthias Meschede et al.',
    license='BSD',
    keywords=KEYWORDS,
    install_requires=INSTALL_REQUIRES,
    platforms='OS Independent',
    packages=['pyshtools'],
    package_data={'': ['doc/*.doc']},
    include_package_data=True,
    classifiers=CLASSIFIERS,
    configuration=configuration,
    cmdclass={'build': SHTOOLS_build}
)


setup(**metadata)