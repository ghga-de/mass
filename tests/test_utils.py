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

"""Test utility functions, for now just the index creation"""
import pytest
from pymongo import TEXT

from mass.core import models
from mass.main import collection_init_and_index_creation
from mass.ports.inbound.query_handler import QueryHandlerPort
from tests.fixtures.joint import JointFixture

CLASS_NAME = "EmptyCollection"
RESOURCE = models.Resource(
    id_="test",
    content={"fun_fact": "The original name for the search engine Google was Backrub."},
)
QUERY_STRING = "Backrub"


async def initial_verification(query_handler: QueryHandlerPort):
    """Convenience function to verify that the collection is empty"""

    first_results = await query_handler.handle_query(
        class_name=CLASS_NAME,
        query="",
        filters=[],
    )

    assert first_results.count == 0


@pytest.mark.parametrize("preexisting_collection", [True, False])
@pytest.mark.parametrize("load_resource", [True, False])
@pytest.mark.asyncio
async def test_index_creation(
    joint_fixture: JointFixture,
    preexisting_collection: bool,
    load_resource: bool,
):
    """Test the index creation function.

    Parameters exist to make sure the function works when there:
     1. is and is not an existing collection
     2. is and is not an index already created

    Also checks that queries will work when the collection remains empty and when it has
    resources loaded.
    """

    query_handler: QueryHandlerPort = await joint_fixture.container.query_handler()

    await initial_verification(query_handler)

    if preexisting_collection:
        joint_fixture.mongodb.client[joint_fixture.config.db_name].create_collection(
            CLASS_NAME
        )

    # verify that we get an error when searching query string
    with pytest.raises(QueryHandlerPort.SearchError):
        await query_handler.handle_query(
            class_name=CLASS_NAME,
            query=QUERY_STRING,
            filters=[],
        )

    # create indexes
    collection_init_and_index_creation(joint_fixture.config)

    # load a resource
    if load_resource:
        await query_handler.load_resource(resource=RESOURCE, class_name=CLASS_NAME)

    # verify that supplying a query string doesn't result in an error
    results = await query_handler.handle_query(
        class_name=CLASS_NAME,
        query=QUERY_STRING,
        filters=[],
    )

    assert results.count == int(load_resource)


@pytest.mark.asyncio
async def test_with_preexisting_index(joint_fixture: JointFixture):
    """Make sure the index creation function doesn't break if an index already exists"""
    query_handler: QueryHandlerPort = await joint_fixture.container.query_handler()

    await initial_verification(query_handler)

    # verify that we get an error when searching query string
    with pytest.raises(QueryHandlerPort.SearchError):
        await query_handler.handle_query(
            class_name=CLASS_NAME,
            query=QUERY_STRING,
            filters=[],
        )

    # create an index
    joint_fixture.mongodb.client[joint_fixture.config.db_name][CLASS_NAME].create_index(
        [("$**", TEXT)]
    )

    # verify that we DO NOT get an error when searching query string
    await query_handler.handle_query(
        class_name=CLASS_NAME,
        query=QUERY_STRING,
        filters=[],
    )

    # call the index creation function
    collection_init_and_index_creation(joint_fixture.config)

    # load a resource
    await query_handler.load_resource(resource=RESOURCE, class_name=CLASS_NAME)

    # verify that supplying a query string doesn't result in an error
    results = await query_handler.handle_query(
        class_name=CLASS_NAME,
        query=QUERY_STRING,
        filters=[],
    )

    assert results.count == 1
