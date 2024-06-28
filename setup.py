from setuptools import find_packages, setup


def get_version_and_cmdclass(package_name):
    import os
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("version", os.path.join(package_name, "_version.py"))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__, module.cmdclass


version, cmdclass = get_version_and_cmdclass("net_worth_tracker")

with open("requirements.txt") as f:
    requirements = [r for r in f.read().split("\n") if r.strip()]

with open("README.md") as f:
    readme = f.read()

setup(
    name="net-worth-tracker",
    version=version,
    cmdclass=cmdclass,
    python_requires=">=3.9",
    packages=find_packages("."),
    maintainer="Bas Nijholt",
    maintainer_email="bas@nijho.lt",
    description="See your current portfolio balance without the hassle.",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="BSD-3",
    url="https://github.com/basnijholt/net-worth-tracker",
    download_url="https://pypi.python.org/pypi/net-worth-tracker",
    install_requires=requirements,
)
