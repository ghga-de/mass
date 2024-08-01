This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.

This service is currently designed to work with MongoDB and uses an aggregation pipeline to produce search results.

Typical sequence of events is as follows:

1. Requests are received by the API, then directed to the QueryHandler in the core.

2. From there, the configuration is consulted to retrieve any facetable and selected fields for the searched resource class.

3. The search parameters and facet fields are passed to the Aggregator, which builds and runs the aggregation pipeline on the appropriate collection. The aggregation pipeline is a series of stages run in sequence:
   1. Run a text match using the query string.
   2. Apply a sort based on the IDs.
   3. Apply any filters supplied in the search parameters.
   4. Extract the facets.
   5. Keep only selected fields if some have been specified.
   6. Transform the results structure into {facets, hits, hit count}.

4. Once retrieved in the Aggregator, the results are passed back to the QueryHandler where they are shoved into a QueryResults Pydantic model for validation before finally being sent back to the API.
