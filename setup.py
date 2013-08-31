from setuptools import setup

setup(name="PySolarized",
      version="1.2.1",
      description="A simple library for accessing Apache Solr full-text search engine. Allows updating and queryies over"
                  "multiple cores.",
      author="Jernej Virag",
      author_email="jernej@virag.si",
      packages=["pysolarized"],
      license="MIT",
      install_requires=["requests"],
      classifiers=[
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Topic :: Software Development :: Libraries",
          "Topic :: Internet :: WWW/HTTP :: Indexing/Search"
])
