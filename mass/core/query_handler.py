# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Contains implementation of a QueryHandler to field queries on metadata"""
from typing import Optional

from hexkit.custom_types import JsonObject

from mass.config import SearchableClassesConfig
from mass.core import models, utils
from mass.ports.inbound.query_handler import ClassNotConfiguredError, QueryHandlerPort
from mass.ports.outbound.aggregator import AggregatorCollectionPort
from mass.ports.outbound.dao import DaoCollectionPort


class QueryHandler(QueryHandlerPort):
    """Concrete implementation of a query handler"""

    def __init__(
        self,
        *,
        config: SearchableClassesConfig,
        aggregator_collection: AggregatorCollectionPort,
        dao_collection: DaoCollectionPort,
    ):
        """Initialize the query handler with resource daos/aggregators"""
        self._config = config
        self._aggregator_collection = aggregator_collection
        self._dao_collection = dao_collection

    async def load_resource(self, *, resource: models.Resource, class_name: str):
        """Helper function to load resources into the database"""
        dao = self._dao_collection.get_dao(class_name=class_name)
        await dao.upsert(resource)

    async def handle_query(
        self,
        *,
        class_name: str,
        query: str,
        filters: list[models.Filter],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> models.QueryResults:
        """Return resources that match query"""

        # get configured facet fields for given resource class
        try:
            facet_fields = self._config.searchable_classes[
                class_name
            ].facetable_properties
        except KeyError as err:
            raise ClassNotConfiguredError(class_name=class_name) from err

        # build the aggregation pipeline
        pipeline = utils.build_pipeline(
            query=query,
            filters=filters,
            facet_fields=facet_fields,
            skip=skip,
            limit=limit,
        )

        # run the aggregation. Results will have {facets, count, hits} format
        aggregator = self._aggregator_collection.get_aggregator(class_name=class_name)
        aggregator_results: list[JsonObject] = await aggregator.aggregate(
            pipeline=pipeline
        )
        query_results = models.QueryResults(**aggregator_results[0])

        # replace __ with . in facet keys
        for i, facet in enumerate(query_results.facets):
            facet.key = facet.key.replace("__", ".")
            query_results.facets[i] = facet
        return query_results
