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

"""Utility functions for building the aggregation pipeline used by query handler"""
from collections import defaultdict
from typing import Any, Optional

from hexkit.custom_types import JsonObject

from mass.core import models


def pipeline_match_text_search(*, query: str) -> JsonObject:
    """Build text search segment of aggregation pipeline"""
    text_search = {"$text": {"$search": query}}
    return {"$match": text_search}


def replace_periods(*, field_name: str) -> str:
    """convert field names with . to __ e.g.: obj.type -> obj__type"""
    return field_name.replace(".", "__")


def args_for_getfield(*, root_object_name: str, field_name: str) -> tuple[str, str]:
    """fieldpath names can't have '.', so specify any nested fields with $getField"""
    prefix = f"${root_object_name}"
    specified_field = field_name
    if "." in field_name:
        pieces = field_name.split(".")
        specified_field = pieces[-1]
        prefix += "." + ".".join(pieces[:-1])

    return (prefix, specified_field)


def pipeline_match_filters_stage(*, filters: list[models.Filter]) -> JsonObject:
    """Build segment of pipeline to apply search filters"""

    segment: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"$in": []})
    for item in filters:
        filter_key = "content." + str(item.key)
        filter_value = item.value
        segment[filter_key]["$in"].append(filter_value)

    return {"$match": segment}


def pipeline_apply_facets(
    *, facet_fields: list[str], skip: int, limit: Optional[int] = None
):
    """Uses a list of facetable property names to build the subquery for faceting"""
    segment: dict[str, list[JsonObject]] = {}

    for field in facet_fields:
        prefix, specified_field = args_for_getfield(
            root_object_name="content", field_name=field
        )

        segment[replace_periods(field_name=field)] = [
            {
                "$group": {
                    "_id": {"$getField": {"field": specified_field, "input": prefix}},
                    "count": {"$sum": 1},
                }
            }
        ]

    # this is the total number of hits, but pagination can mean only a few are returned
    segment["count"] = [{"$count": "total"}]

    # sort by ID, then rename the ID field to id_ to match our model
    segment["hits"] = [
        {"$sort": {"_id": 1}},
        {"$addFields": {"id_": "$_id"}},
        {"$unset": "_id"},
    ]

    # apply skip and limit for pagination
    if skip > 0:
        segment["hits"].append({"$skip": skip})

    if limit:
        segment["hits"].append({"$limit": limit})

    return {"$facet": segment}


def pipeline_project(*, facet_fields: list[str]) -> JsonObject:
    """Reshape the query so the facets are contained in a top level object"""
    segment: dict[str, Any] = {"hits": 1, "facets": []}
    segment["count"] = {"$arrayElemAt": ["$count.total", 0]}

    # add a segment for each facet to summarize the options
    for facet_name in facet_fields:
        facet_name = facet_name.replace(".", "__")
        segment["facets"].append(
            {
                "key": facet_name,
                "options": {
                    "$map": {
                        "input": f"${facet_name}",
                        "as": "temp",
                        "in": {"option": "$$temp._id", "count": "$$temp.count"},
                    }
                },
            }
        )
    return {"$project": segment}


def build_pipeline(
    *,
    query: str,
    filters: list[models.Filter],
    facet_fields: list[str],
    skip: int = 0,
    limit: Optional[int] = None,
) -> list[JsonObject]:
    """Build aggregation pipeline based on query"""
    pipeline: list[JsonObject] = []
    query = query.strip()

    # perform text search
    if query:
        pipeline.append(pipeline_match_text_search(query=query))

    # sort initial results
    pipeline.append({"$sort": {"_id": 1}})

    # apply filters
    if filters:
        pipeline.append(pipeline_match_filters_stage(filters=filters))

    # define facets from preliminary results and reshape data
    if facet_fields:
        pipeline.append(
            pipeline_apply_facets(facet_fields=facet_fields, skip=skip, limit=limit)
        )

    # transform data one more time to match models
    pipeline.append(pipeline_project(facet_fields=facet_fields))

    return pipeline
