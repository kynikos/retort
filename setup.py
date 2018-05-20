from setuptools import setup, find_packages

setup(
    # 'retort' was taken in October 2017 even though I made this library in
    # 2016; reminder to self, publish as soon as ready
    name='retort-cgi',
    version='1.0.1',
    description=('Lightweight Python CGI framework.'),
    long_description=('Lightweight Python CGI framework.'),
    url='https://github.com/kynikos/retort',
    author='Dario Giovannetti',
    author_email='dev@dariogiovannetti.net',
    license='GPLv3+',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries',  # noqa
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',  # noqa
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='html web development',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
)
