from solr import Solr, SolrException, SolrResults

__all__ = ["Solr", "SolrException", "SolrResults"]


# Converts passed timezone-aware datetime object to ISO8601 format Solr expects
def to_solr_date(date):
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")