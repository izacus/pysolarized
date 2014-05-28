from setuptools import setup

setup(name="PySolarized",
      version="1.4.1",
      description="A simple library for accessing Apache Solr full-text search engine. Allows updating and queries over"
                  "multiple cores.",
      author="Jernej Virag",
      author_email="jernej@virag.si",
      packages=["pysolarized"],
      url="https://github.com/izacus/pysolarized",
      license="MIT",
      install_requires=["requests", "httpcache"],
      classifiers=[
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Topic :: Software Development :: Libraries",
          "Topic :: Internet :: WWW/HTTP :: Indexing/Search"
])
