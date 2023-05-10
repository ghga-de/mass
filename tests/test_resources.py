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

"""Basic tests for presence of resources/documents in the database"""

# pylint: disable=redefined-outer-name

import pytest
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    MongoDbFixture,
    mongodb_fixture,
)

from mass.adapters.outbound.dao import DaoNotFoundError
from mass.core import models
from tests.fixtures.joint import JointFixture, joint_fixture  # noqa: F401
from tests.fixtures.mongo import populated_mongodb_fixture  # noqa: F401


@pytest.mark.asyncio
async def test_basic_query_and_load(joint_fixture: JointFixture):  # noqa: F811
    """Make sure we can pull back the documents that are stored as well as load more"""

    query_handler = await joint_fixture.container.query_handler()
    results = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="mundane", filters=[], skip=0, limit=10
    )

    assert len(results) == 2

    results_2 = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="invaluable", filters=[], skip=0, limit=10
    )

    assert len(results_2) == 1

    results_filtered = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="stoncher",
        filters=[models.Filter(key="field1", value="Beta")],
        skip=0,
        limit=10,
    )

    assert len(results_filtered) == 1

    # get all the documents in the collection
    results_all = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="",
        filters=[],
        skip=0,
        limit=0,
    )

    # define and load a new resource
    resource = models.Resource(
        id_="jf2jl-dlasd82",
        content={
            "has_feature": {"feature_name": "added_resource", "id": "98u44-f4jo4"}
        },
    )

    await query_handler.load_resource(resource=resource, class_name="DatasetEmbedded")

    # make sure the new resource is added to the collection
    results_after_load = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[], skip=0, limit=0
    )
    assert len(results_after_load) - len(results_all) == 1

    target_search = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="added_resource",
        filters=[],
        skip=0,
        limit=0,
    )
    assert len(target_search) == 1
    validated_resource = target_search[0]
    assert validated_resource.id_ == resource.id_
    assert validated_resource.content == resource.content

    # make sure limit works
    results_limited = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[], skip=0, limit=2
    )
    assert len(results_limited) == 2


@pytest.mark.skip
async def test_absent_resource(joint_fixture: JointFixture):  # noqa: F811
    """Make sure we get an error when looking for a resource type that doesn't exist"""
    query_handler = await joint_fixture.container.query_handler()
    with pytest.raises(DaoNotFoundError):
        await query_handler.handle_query(class_name="does_not_exist")
