from __future__ import unicode_literals
import json
import logging
from httpcache import CachingHTTPAdapter
import itertools
import requests

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

SOLR_ADD_BATCH = 200 # Number of documents to send in batch when adding
logger = logging.getLogger("pysolarized")


# Builds URL from base and path
def _get_url(base, path):
    return '/'.join(s.strip('/') for s in itertools.chain([base, path]))


# Class holding search results
class SolrResults:
    def __init__(self):
        self.query_time = None      # Time the query took
        self.results_count = None   # Number of found results
        self.start_index = None     # Index of start
        self.documents = []         # Found results
        self.facets = {}            # Found facet counts
        self.highlights = {}        # Highligts for found documents


class SolrException(BaseException):
    pass


class Solr(object):
    def __init__(self, endpoints, default_endpoint=None, http_cache=True):
        if not endpoints:
            logger.warning("Faulty Solr configuration, SOLR will not be available!")
            return

        self.endpoints = None
        self.default_endpoint = None
        self._shards = None
        self._add_batch = list()
        self.req_session = requests.Session()

        if http_cache:
            self.req_session.mount("http://", CachingHTTPAdapter())
            self.req_session.mount("https://", CachingHTTPAdapter())

        if self._is_string(endpoints):
            self.endpoints = {'default': endpoints}
            self.default_endpoint = "default"
        else:
            self.endpoints = endpoints
            if default_endpoint:
                self.default_endpoint = default_endpoint
            else:
                self.default_endpoint = endpoints[0]

    def _is_string(self, obj):
        try:
            return isinstance(obj, basestring)  # Python 2
        except NameError:
            return isinstance(obj, str)         # Python 3

    def _send_solr_command(self, core_url, json_command):
        """
        Sends JSON string to Solr instance
        """

        # Check document language and dispatch to correct core
        url = _get_url(core_url, "update")
        try:
            response = self.req_session.post(url, data=json_command, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to send update to Solr endpoint [%s]: %s", core_url, e, exc_info=True)
            raise SolrException("Failed to send command to Solr [%s]: %s" % (core_url, e,))
        return True

    def _send_solr_query(self, request_url, query):
        try:
            response = self.req_session.post(request_url, data=query)
            response.raise_for_status()
            results = response.json()
        except requests.RequestException as e:
            logger.error("Failed to connect to Solr server: %s!", e, exc_info=True)
            return None
        return results

    def add(self, documents, boost=None):
        """
        Adds documents to Solr index
        documents - Single item or list of items to add
        """

        if not isinstance(documents, list):
            documents = [documents]
        documents = [{'doc': d} for d in documents]
        if boost:
            for d in documents:
                d['boost'] = boost

        self._add_batch.extend(documents)

        if len(self._add_batch) > SOLR_ADD_BATCH:
            self._addFlushBatch()

    def _addFlushBatch(self):
        """
        Sends all waiting documents to Solr
        """

        if len(self._add_batch) > 0:
            language_batches = {}
            # Create command JSONs for each of language endpoints
            for lang in self.endpoints:
                # Append documents with languages without endpoint to default endpoint
                document_jsons = ["\"add\":" + json.dumps(data) for data in self._add_batch
                                  if data['doc'].get("language", self.default_endpoint) == lang or (lang == self.default_endpoint and not self.endpoints.has_key(data['doc'].get("language", None)))]
                command_json = "{" + ",".join(document_jsons) + "}"
                language_batches[lang] = command_json
            # Solr requires for documents to be sent in { "add" : { "doc" : {...} }, "add": { "doc" : { ... }, ... }
            # format which isn't possible with python dictionaries
            for lang in language_batches:
                self._send_solr_command(self.endpoints[lang], language_batches[lang])
                self._add_batch = []

    def deleteAll(self):
        """
        Deletes whole Solr index. Use with care.
        """
        for core in self.endpoints:
            self._send_solr_command(self.endpoints[core], "{\"delete\": { \"query\" : \"*:*\"}}")

    def delete(self, id):
        """
        Deletes document with ID on all Solr cores
        """
        for core in self.endpoints:
            self._send_solr_command(self.endpoints[core], "{\"delete\" : { \"id\" : \"%s\"}}" % (id,))

    def commit(self):
        """
        Flushes all pending changes and commits Solr changes
        """
        self._addFlushBatch()
        for core in self.endpoints:
            self._send_solr_command(self.endpoints[core], "{ \"commit\":{} }")

    def optimize(self):
        for core in self.endpoints:
            self._send_solr_command(self.endpoints[core], "{ \"optimize\": {} }")

    def _get_shards(self):
        """
        Returns comma separated list of configured Solr cores
        """
        if self._shards is None:
            endpoints = []
            for endpoint in self.endpoints:
                # We need to remove and http:// prefixes from URLs
                url = urlparse.urlparse(self.endpoints[endpoint])
                endpoints.append("/".join([url.netloc, url.path]))
            self._shards = ",".join(endpoints)
        return self._shards

    def _parse_response(self, results):
        """
        Parses result dictionary into a SolrResults object
        """

        dict_response = results.get("response")
        result_obj = SolrResults()
        result_obj.query_time = results.get("responseHeader").get("QTime", None)
        result_obj.results_count = dict_response.get("numFound", 0)
        result_obj.start_index = dict_response.get("start", 0)

        for doc in dict_response.get("docs", []):
            result_obj.documents.append(doc)

        # Process facets
        if "facet_counts" in results:
            facet_types = ["facet_fields", "facet_dates", "facet_ranges", "facet_queries"]
            for type in facet_types:
                assert type in results.get("facet_counts")
                items = results.get("facet_counts").get(type)
                for field, values in items.items():
                    result_obj.facets[field] = []

                    # Range facets have results in "counts" subkey and "between/after" on top level. Flatten this.
                    if type == "facet_ranges":
                        if not "counts" in values:
                            continue

                        for facet, value in values["counts"].items():
                            result_obj.facets[field].append((facet, value))

                        if "before" in values:
                            result_obj.facets[field].append(("before", values["before"]))

                        if "after" in values:
                            result_obj.facets[field].append(("after", values["after"]))
                    else:
                        for facet, value in values.items():
                            # Date facets have metadata fields between the results, skip the params, keep "before" and "after" fields for other
                            if type == "facet_dates" and \
                            (facet == "gap" or facet == "between" or facet == "start" or facet == "end"):
                                continue
                            result_obj.facets[field].append((facet, value))

        # Process highlights
        if "highlighting" in results:
            for key, value in results.get("highlighting").items():
                result_obj.highlights[key] = value

        return result_obj

    def query(self, query, filters=None, columns=None, sort=None, start=0, rows=30):
        """
        Queries Solr and returns results

        query - Text query to search for
        filters - dictionary of filters to apply when searching in form of { "field":"filter_value" }
        columns - columns to return, list of strings
        sort - list of fields to sort on in format of ["field asc", "field desc", ... ]
        start - start number of first result (used in pagination)
        rows - number of rows to return (used for pagination, defaults to 30)
        """

        if not columns:
            columns = ["*", "score"]

        fields = {"q": query,
                 "json.nl" :"map",           # Return facets as JSON objects
                 "fl": ",".join(columns),    # Return score along with results
                 "start": str(start),
                 "rows": str(rows),
                 "wt": "json"}

        # Use shards parameter only if there are several cores active
        if len(self.endpoints) > 1:
            fields["shards"] = self._get_shards()

        # Prepare filters
        if not filters is None:
            filter_list = []
            for filter_field, value in filters.items():
                filter_list.append("%s:%s" % (filter_field, value))
            fields["fq"] = " AND ".join(filter_list)

        # Append sorting parameters
        if not sort is None:
            fields["sort"] = ",".join(sort)

        # Do request to Solr server to default endpoint (other cores will be queried with shard functionality)
        assert self.default_endpoint in self.endpoints
        request_url = _get_url(self.endpoints[self.default_endpoint], "select")
        results = self._send_solr_query(request_url, fields)
        if not results:
            return None

        assert "responseHeader" in results
        # Check for response status
        if not results.get("responseHeader").get("status") == 0:
            logger.error("Server error while retrieving results: %s", results)
            return None

        assert "response" in results

        result_obj = self._parse_response(results)
        return result_obj

    def more_like_this(self, query, fields, columns=None, start=0, rows=30):
        """
        Retrieves "more like this" results for a passed query document

        query - query for a document on which to base similar documents
        fields - fields on which to base similarity estimation (either comma delimited string or a list)
        columns - columns to return (list of strings)
        start - start number for first result (used in pagination)
        rows - number of rows to return (used for pagination, defaults to 30)
        """
        if isinstance(fields, basestring):
            mlt_fields = fields
        else:
            mlt_fields = ",".join(fields)

        if columns is None:
            columns = ["*", "score"]

        fields = {'q' : query,
                  'json.nl': 'map',
                  'mlt.fl': mlt_fields,
                  'fl': ",".join(columns),
                  'start': str(start),
                  'rows': str(rows),
                  'wt': "json"}

        if len(self.endpoints) > 1:
            fields["shards"] = self._get_shards()

        assert self.default_endpoint in self.endpoints
        request_url = _get_url(self.endpoints[self.default_endpoint], "mlt")
        results = self._send_solr_query(request_url, fields)
        if not results:
            return None

        assert "responseHeader" in results
        # Check for response status
        if not results.get("responseHeader").get("status") == 0:
            logger.error("Server error while retrieving results: %s", results)
            return None

        assert "response" in results

        result_obj = self._parse_response(results)
        return result_obj
