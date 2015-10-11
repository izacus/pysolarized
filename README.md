# pysolarized

[![Build Status](https://travis-ci.org/izacus/pysolarized.png)](https://travis-ci.org/izacus/pysolarized)

Yet another library for talking to Solr with Python with language and sharding support.

Supported Python versions: 2.6, 2.7, 3.2, 3.3, 3.4, 3.5

## Installation

Install it from PyPi with

```python
pip install pysolarized
```

## Simple usage

Communication with Solr is done via `Solr` class instance configured with endpoints.

Single Solr core is used by just passing the core URL to the constructor

```python
import pysolarized
solr = pysolarized.solr.Solr("http://localhost:8080/solr/core1")
```

If there are multiple endpoints for multiple languages, you have to pass dictionary of endpoints and default endpoint which will take documents with unrecognised language.

```python
import pysolarized
solr = pysolarized.solr.Solr({"en": "http://localhost:8080/solr/core-en", "si": "http://localhost:8080/solr/core-si"}, default_endpoint="en")
```

### Queries

Queries are automatically done over all configured cores and results are aggregated automatically. Just call the `query` method

```python
results = solr.query("Ljubljana", 
					filters = {"country": "Slovenia" },
					columns = ["id", "city_name"],
					sort = ["city_name desc"],	
					start = 0,
					num_rows = 20)					
```

All parameters except the query string itself are optional.

Query call returns an instance of `SolrResults` class or None if there was a network/server error while executing the query.

```python
class SolrResults:
    def __init__(self):
        self.query_time = None      # Time the query took
        self.results_count = None   # Number of found results
        self.start_index = None     # Index of start
        self.documents = []         # Found results
        self.facets = {}            # Found facet counts
        self.highlights = {}        # Highligts for found documents
```

### Adding documents

Documents are represented as a python dictionary with field names as keys. To insert new documents into Solr index call the `add` method with list of documents and `commit` after all insertions have been completed.

```python
solr.add([ { "id": "c1en", "city_name": "Vienna", "country": "Austria", "language": "en" }, 
		   { "id": "c1si", "city_name": "Dunaj", "country": "Avstrija", "language": "si"}])
solr.commit()
```

Note that pysolarized will look for `language` field in the document to determine to which Solr core the document will be dispatched to. If the field is missing or the value doesn't match any of configured cores, it'll dispatch the document to the default endpoint.

### Other actions

To delete a document from server use the `delete` call and `commit` afterwards:

```python
solr.delete("c1en")
solr.commit()
```

To clear all data from all cores use `deleteAll`

```python
solr.deleteAll()
solr.commit()
```
