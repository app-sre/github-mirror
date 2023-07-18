from setuptools import setup, find_packages


setup(name='ghmirror',
      packages=find_packages(),
      version=open('VERSION').read().strip(),
      author='Red Hat Application SRE Team',
      author_email="sd-app-sre@redhat.com",
      description='GitHub API mirror that caches the responses and implements '
                  'conditional requests, serving the client with the cached '
                  'responses when the GitHub API replies with a 304 HTTP '
                  'code, reducing the number of API calls, making a more '
                  'efficient use of the GitHub API rate limit.',
      python_requires='>=3.6',
      license="GPLv2+",
      classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'Environment :: Web Environment',
            'Framework :: Flask',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: '
            'GNU General Public License v2 or later (GPLv2+)',
            'Natural Language :: English',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
      ],
      install_requires=['Flask~=1.1',
                        'requests~=2.22',
                        'prometheus_client~=0.7',
                        'gunicorn==20.1.0',
                        'redis~=3.5',
                        'MarkupSafe==2.0.1'])
