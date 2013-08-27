# -*- coding: utf-8 -*-
import json
import unittest
from pysolarized.solr import Solr


class TestInstrumentation(unittest.TestCase):

    def testUrlJoin(self):
        from solr import _get_url
        url = _get_url("http://example.com", "/update/")
        self.assertEquals(url, "http://example.com/update")
        url = _get_url("http://example.com/", "/update")
        self.assertEquals(url, "http://example.com/update")
        url = _get_url("http://example.com", "update")
        self.assertEquals(url, "http://example.com/update")
        url = _get_url("127.0.0.1", "something/something/darkside")
        self.assertEquals(url, "127.0.0.1/something/something/darkside")


class TestSolrUpdates(unittest.TestCase):

    def setUp(self):
        self._clear_handler()

    def _command_handler(self, url, command):
        self.req_urls.append(url)
        self.req_commands.append(command)

    def _clear_handler(self):
        self.req_urls = []
        self.req_commands = []

    def testSolrInterface(self):
        # Check configuration with string only
        url = "http://this.is.a.mock.url"
        solr = Solr(url)
        solr._send_solr_command = self._command_handler
        solr.commit()
        self.assertEquals(self.req_urls[0], url)

    def testUpdateDispatch(self):
        url = "http://this.is.a.failure.fail"
        document1 = {u"name": u"Joe", u"surname": u"Satriani", u"booboo": 12}
        document2 = {u"name": u"Joanna", u"surname": u"S šuuumnikiiiič!", u"booboo": 12}

        solr = Solr({"en": url}, "en")
        solr._send_solr_command = self._command_handler
        solr.add([document1])
        solr.commit()

        self.assertEquals(self.req_urls[0], url)
        self.assertEquals(self.req_urls[1], url)
        self.assertDictEqual({"add": {"doc": document1}}, json.loads(self.req_commands[0]))
        self.assertDictEqual({"commit": {}}, json.loads(self.req_commands[1]))

        self._clear_handler()
        solr.add([document1, document2])
        solr.commit()

        self.assertEquals(self.req_urls[0], url)
        self.assertEquals(self.req_urls[1], url)

        self.assertEquals(self.req_commands[0], u"{\"add\":{\"doc\": %s},\"add\":{\"doc\": %s}}" % (json.dumps(document1),
                                                                                                    json.dumps(document2)))
        self.assertDictEqual({"commit": {}}, json.loads(self.req_commands[1]))


class testSolrQueries(unittest.TestCase):

    query_response = """
        { "responseHeader": { "status":0, "QTime" : 45 },
          "response" : { "numFound" : 1, "start": 31,
                         "docs" : [ {"title" : "This is woot", "content" : "This isn't woot." } ]},
          "facet_counts": { "facet_fields" : { "source" : { "newspaper" : 342 }}, "facet_dates":{},"facet_queries":{}, "facet_ranges":{}},
          "highlighting": { "ididid" : { "content": [ "... blah blah ..."]}}}
    """

    def _query_handler(self, url, command):
        self.query_url = url
        self.query_params = command
        return json.loads(self.query_response)

    def setUp(self):
        self.query_url = None
        self.query_params = None

    def testQueryDispatch(self):
        url = "http://this.is.a.failure.fail"
        solr = Solr({"en": url}, "en")
        solr._send_solr_query = self._query_handler

        query = u"what is a treeš"
        filters = {"meaning": "deep"}
        sort = ["deepness", "wideness"]
        columns = ["title", "content"]
        start = 31
        rows = 84

        results = solr.query(query,
                             filters=filters,
                             columns=columns,
                             sort=sort,
                             start=start,
                             rows=rows)

        self.assertEquals(self.query_url, "%s/select" % (url,))
        expected = [('q', query),
                    ('json.nl', 'map'),
                    ('fl', ",".join(columns)),
                    ('start', str(start)),
                    ('rows', str(rows)),
                    ('fq', '%s:%s' % (filters.keys()[0], filters.values()[0])),
                    ('sort', ",".join(sort))]
        self.assertListEqual(self.query_params, expected)
        self.assertIsNotNone(results)

        # Check results
        self.assertEquals(results.results_count, 1)
        self.assertEquals(results.query_time, 45)
        self.assertDictEqual(results.documents[0], {"title": "This is woot", "content": "This isn't woot."})
        self.assertDictEqual(results.facets, {"source": [("newspaper", 342)]})
        self.assertDictEqual(results.highlights, {'ididid': {"content": ["... blah blah ..."]}})

if __name__ == "__main__":
    unittest.main()