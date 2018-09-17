Versioning scheme for Scuba
=============================

The following versioning scheme has been developed to make it easier to release
new versions of Scuba, while allowing users to always have an accurate idea
of the version they are running.

Versions are driven by a "base version", which is kept in `scuba/version.py`
and is manually updated before each release. This base version follows
[Semantic Versioning](http://semver.org/), and is augmented with additional
information, depending on the environment and they way the software has been
obtained.

There are two different places the Scuba version is maintained; the goal is
to ensure these are always in-sync:

1. The `scuba.version.__version__` attribute. This is what is displayed when
   `scuba --version` is run.

2. The metadata, as seen by Pip and on PyPI.

Scuba can be acquired in various ways, each with its own impact on the
versioning scheme. Consider a base version of `1.2.3`:

1. **PyPI** - Scuba is only deployed to the main PyPI site when a new version
   is tagged. Thus, the version on PyPI will always be nothing more than the
   base version.

2. **Test PyPI** - Scuba is automatically deployed (via Travis-CI) to the
   [PyPI Testing Site](testpypi.python.org) upon each push to the `master`
   branch. PyPI requires non-local [PEP 440](https://www.python.org/dev/peps/pep-0440)
   -compliant versions. Because of this, the Travis CI build number is appended
   to the base version, excluding any Git information, e.g. `1.2.3.456` where
   `456` is the build number. This ensures that the latest build on `master`
   will always be deployed to PyPI testing as the newest version.

3. **Git clone** - Scuba can be run from a local Git repository.
   In this case, the version presented by Scuba will come from the output
   of `git describe`, and will look like this: `1.2.3-45-gabcdef`,
   where `-45` is the number of commits since version `1.2.3`, and `abcdef`
   is the hash of the current commit. The version may also include `-dirty`
   if there are any uncommitted modifications to the code.

4. **Git archive** - Scuba can be run from an archive of the Git repository,
   either from `git archive` or by downloading a source tarball from GitHub.
   In this case, the version presented by Scuba will come from substituions
   made by Git during archive creation, controlled by the `export-subst`
   attribute. The version will look like this: `1.2.3-gabcdef`, where `abcdef`
   is the hash of the current commit.

5. **Source distribution** - Scuba can be run from a source distribution,
   created via `python setup.py sdist`. In this case, the version comes from
   the egg info generated by setuptools.

In any case, when Scuba is installed, the version comes from `pkg_resources`.