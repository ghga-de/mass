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

"""Test index creation"""

import pytest
from pymongo import TEXT

from mass.core import models
from tests.fixtures.joint import JointFixture

CLASS_NAME = "EmptyCollection"
RESOURCE = models.Resource(
    id_="test",
    content={"fun_fact": "The original name for the search engine Google was Backrub."},
)
QUERY_STRING = "Backrub"


@pytest.mark.parametrize("create_index_manually", [False, True], ids=["auto", "manual"])
@pytest.mark.asyncio()
async def test_index_creation(joint_fixture: JointFixture, create_index_manually: bool):
    """Test the index creation function."""
    # indexes have been created in fixture setup, so delete them again
    joint_fixture.purge_database()

    # verify collection does not exist
    database = joint_fixture.mongodb_client[joint_fixture.config.db_name]
    assert CLASS_NAME not in database.list_collection_names()

    # let the query handler know that it needs to run the indexing function
    joint_fixture.recreate_mongodb_indexes()

    # make sure we do not get an error when trying to query non-existent collection
    results_without_coll = await joint_fixture.handle_query(
        class_name=CLASS_NAME, query=QUERY_STRING
    )
    # should have received empty results model
    assert results_without_coll == models.QueryResults()

    # create collection without index
    joint_fixture.mongodb_client[joint_fixture.config.db_name].create_collection(
        CLASS_NAME
    )

    # verify collection exists
    assert CLASS_NAME in database.list_collection_names()

    collection = database[CLASS_NAME]

    # verify collection does not have the text index
    assert not any(
        index["name"] == f"$**_{TEXT}" for index in collection.list_indexes()
    )

    # Verify querying empty collection with query string gives empty results model
    results_without_coll = await joint_fixture.handle_query(
        class_name=CLASS_NAME,
        query=QUERY_STRING,
    )
    assert results_without_coll == models.QueryResults()

    if create_index_manually:
        # check that the index creation function works when an index is already present
        collection.create_index([("$**", TEXT)])
        assert any(
            index["name"] == f"$**_{TEXT}" for index in collection.list_indexes()
        )

    # load a resource
    await joint_fixture.load_resource(resource=RESOURCE, class_name=CLASS_NAME)

    # verify the text index exists now
    assert any(index["name"] == f"$**_{TEXT}" for index in collection.list_indexes())

    # verify that supplying a query string doesn't result in an error
    results_with_coll = await joint_fixture.handle_query(
        class_name=CLASS_NAME, query=QUERY_STRING
    )

    assert results_with_coll.count == 1
    assert results_with_coll.hits[0] == RESOURCE
