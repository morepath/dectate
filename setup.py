import io
from setuptools import setup, find_packages

long_description = "\n".join(
    (
        io.open("README.rst", encoding="utf-8").read(),
        io.open("CHANGES.txt", encoding="utf-8").read(),
    )
)

setup(
    name="dectate",
    version="0.14",
    description="A configuration engine for Python frameworks",
    long_description=long_description,
    author="Martijn Faassen",
    author_email="faassen@startifact.com",
    url="http://dectate.readthedocs.io",
    license="BSD",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Development Status :: 5 - Production/Stable",
    ],
    keywords="configuration",
    install_requires=["setuptools"],
    extras_require=dict(
        test=["pytest >= 2.9.0", "pytest-remove-stale-bytecode"],
        coverage=["pytest-cov"],
        pep8=["flake8", "black"],
        docs=["sphinx"],
    ),
)
