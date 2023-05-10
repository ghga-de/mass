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
from typing import Dict, List, Set

from hexkit.custom_types import JsonObject

from mass.core import models
from mass.ports.inbound.query_handler import QueryHandlerPort
from mass.ports.outbound.aggregator import AggregatorCollectionPort
from mass.ports.outbound.dao import DaoCollectionPort


class QueryHandler(QueryHandlerPort):
    """Concrete implementation of a query handler"""

    def __init__(
        self,
        *,
        aggregator_collection: AggregatorCollectionPort,
        dao_collection: DaoCollectionPort,
    ):
        """Initialize the query handler with resource daos/aggregators"""
        self._aggregator_collection = aggregator_collection
        self._dao_collection = dao_collection

    def _get_nested_fields(self, *, fields: List) -> Set:
        """
        Get nested fields from a given set of fields.

        Args:
            fields: A list of fields

        Returns:
            A set of nested fields

        """
        nested_fields = set()
        for field in fields:
            if "." in field:
                top_level_field, nested_field = field.split(".", 1)
                nested_fields.add((top_level_field, nested_field))
        return nested_fields

    def _pipeline_match_text_search(self, *, query: str) -> JsonObject:
        """Build text search segment of aggregation pipeline"""
        text_search = {"$text": {"$search": query}}
        return {"$match": text_search}

    def _pipeline_match_filters_stage(
        self, *, filters: list[models.Filter]
    ) -> JsonObject:
        """Build segment of pipeline to apply search filters"""
        segment: Dict = {}
        for item in filters:
            filter_key = "content." + str(item.key)
            filter_value = item.value
            try:
                segment[filter_key]["$in"].append(filter_value)
            except KeyError:
                segment[filter_key] = {"$in": [filter_value]}
        return {"$match": segment}

    def _build_pipeline(
        self, *, query: str, filters: list[models.Filter], skip: int, limit: int
    ) -> list[JsonObject]:
        """Build aggregation pipeline based on query"""
        pipeline = []
        query = query.strip()
        if query:
            pipeline.append(self._pipeline_match_text_search(query=query))

        pipeline.append({"$sort": {"_id": 1}})

        if filters:
            pipeline.append(self._pipeline_match_filters_stage(filters=filters))

        pipeline.append({"$skip": skip})
        if limit > 0:
            pipeline.append({"$limit": limit})

        return pipeline

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
        skip: int,
        limit: int,
    ):
        """Return resources that match query"""
        pipeline = self._build_pipeline(
            query=query, filters=filters, skip=skip, limit=limit
        )
        aggregator = self._aggregator_collection.get_aggregator(class_name=class_name)
        results = await aggregator.aggregate(pipeline=pipeline)
        return results
