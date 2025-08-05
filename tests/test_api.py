# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests to assess API functionality"""

import logging

import httpx
import pytest
from hexkit.providers.mongodb.provider import ConfiguredMongoClient

from mass.core import models
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture, QueryParams

pytestmark = pytest.mark.asyncio()

CLASS_NAME = "NestedData"


def compare(
    *,
    results: models.QueryResults,
    count: int,
    hit_length: int,
    hits: list[models.Resource] | None = None,
    facets: list[models.Facet] | None = None,
) -> None:
    """Perform common comparisons for results"""
    assert results.count == count
    assert len(results.hits) == hit_length

    if facets:
        assert results.facets == facets
    else:
        config = get_config()
        dataset_embedded_class = config.searchable_classes[CLASS_NAME]
        assert dataset_embedded_class is not None
        configured_facets = dataset_embedded_class.facetable_fields
        assert len(results.facets) == len(configured_facets)
        assert {x.key for x in results.facets} == {x.key for x in configured_facets}

    if hits:
        assert results.hits == hits


async def test_health_check(joint_fixture: JointFixture):
    """Test that the health check endpoint works."""
    response = await joint_fixture.rest_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


async def test_search_options(joint_fixture: JointFixture):
    """Verify that we can request the configured resource class information correctly"""
    response = await joint_fixture.rest_client.get(url="/search-options")

    assert response.json() == joint_fixture.config.model_dump()["searchable_classes"]


async def test_malformed_document(
    joint_fixture: JointFixture, caplog: pytest.LogCaptureFixture
):
    """Test behavior from API perspective upon querying when bad doc exists"""
    joint_fixture.purge_database()

    # define and load a new resource without all the required facets
    resource = models.Resource(
        id_="added-resource",
        content={
            "object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
            "city": 42,  # expected to be a string
            "category": "test object",
        },
    )

    await joint_fixture.load_resource(resource=resource, class_name=CLASS_NAME)
    params: QueryParams = {"class_name": CLASS_NAME}

    with caplog.at_level(logging.WARNING):
        with pytest.raises(
            httpx.HTTPStatusError, match="500 Internal Server Error"
        ) as exc_info:
            await joint_fixture.call_search_endpoint(params)
        assert (
            exc_info.value.response.json().get("detail")
            == "An error occurred during the search operation"
        )
        assert len(caplog.records) == 1
        msg = caplog.records[0].message
        assert "Input should be a valid string" in msg
        assert "type=string_type, input_value=42, input_type=int" in msg


async def test_search(joint_fixture: JointFixture):
    """Basic query to pull back all documents for class name"""
    params: QueryParams = {"class_name": CLASS_NAME}

    results = await joint_fixture.call_search_endpoint(params)
    compare(results=results, count=3, hit_length=3)


async def test_search_with_limit(joint_fixture: JointFixture):
    """Make sure we get a count of 3 but only 1 hit"""
    params: QueryParams = {"class_name": CLASS_NAME, "limit": 1}

    results = await joint_fixture.call_search_endpoint(params)
    hit = {
        "id_": "1HotelAlpha-id",
        "content": {
            "type": "resort",
            "object": {"type": "piano"},
        },
    }
    hits = [models.Resource(**hit)]  # type: ignore[arg-type]
    compare(results=results, count=3, hit_length=1, hits=hits)


async def test_search_keywords(joint_fixture: JointFixture):
    """Make sure the query string is passed through intact"""
    params: QueryParams = {"class_name": CLASS_NAME, "query": "hotel"}

    results = await joint_fixture.call_search_endpoint(params)
    compare(results=results, count=2, hit_length=2)


async def test_search_filters(joint_fixture: JointFixture):
    """Make sure filters work"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": ["object.type"],
        "value": ["piano"],
    }

    results = await joint_fixture.call_search_endpoint(params)
    compare(results=results, count=1, hit_length=1)


async def test_search_invalid_class(joint_fixture: JointFixture):
    """Verify that searching with a bad class name results in a 422"""
    params: QueryParams = {"class_name": "InvalidClassName", "limit": 1}

    with pytest.raises(httpx.HTTPStatusError, match="422 Unprocessable Entity"):
        await joint_fixture.call_search_endpoint(params)


async def test_auto_recreation_of_indexes(
    joint_fixture: JointFixture, caplog: pytest.LogCaptureFixture
):
    """Make sure the indexes are recreated on the fly when they were deleted"""
    params: QueryParams = {"class_name": CLASS_NAME, "query": "hotel"}

    # should not give a warning when indexes are present
    with caplog.at_level(logging.WARNING):
        await joint_fixture.call_search_endpoint(params)
        assert not caplog.records

    # drop all text indexes
    config = joint_fixture.config
    with ConfiguredMongoClient(config=config) as client:
        db = client[config.db_name]
        for collection_name in db.list_collection_names():
            collection = db[collection_name]
            for index in collection.list_indexes():
                if "text" in index["key"].values():
                    collection.drop_index(index["name"])

    # should work, but give a warning when indexes are recreated
    with caplog.at_level(logging.WARNING):
        results = await joint_fixture.call_search_endpoint(params)
        compare(results=results, count=2, hit_length=2)

        assert len(caplog.records) == 1
        msg = caplog.records[0].message
        assert "Missing text indexes, trying to recreate them" in msg
