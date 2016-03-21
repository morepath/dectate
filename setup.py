from setuptools import setup, find_packages

long_description = (
    open('README.rst').read()
    + '\n' +
    open('CHANGES.txt').read())

setup(name='confidant',
      version='0.1.dev0',
      description="A configuration engine for Python frameworks",
      long_description=long_description,
      author="Martijn Faassen",
      author_email="faassen@startifact.com",
      url='http://confidant.readthedocs.org',
      license="BSD",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      classifiers=[
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Programming Language :: Python :: 2.7',
          'Development Status :: 4 - Beta'
      ],
      keywords="configuration",
      install_requires=[
          'setuptools',
          'venusifork',
      ],
      extras_require = dict(
          test=['pytest >= 2.5.2',
                'py >= 1.4.20',
                'pytest-cov',
                'pytest-remove-stale-bytecode',
          ],
      ),
)
