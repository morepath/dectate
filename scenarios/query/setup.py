from setuptools import setup, find_packages

setup(
    name='query',
    version='0.1.dev0',
    description="A test package with config info to query",
    author="Martijn Faassen",
    author_email="faassen@startifact.com",
    url='http://dectate.readthedocs.org',
    license="BSD",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'decq = query.main:query_tool',
        ]
    },
    install_requires=[
        'setuptools'
    ],
)
