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

"""Basic tests for presence of resources/documents in the database"""

import pytest

from mass.core import models
from mass.ports.inbound.query_handler import QueryHandlerPort
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()


CLASS_NAME = "NestedData"


async def test_basic_query(joint_fixture: JointFixture):
    """Make sure we can pull back the documents as expected"""
    # pull back all 3 test documents
    results = await joint_fixture.handle_query(class_name=CLASS_NAME)

    assert results.count == 3


async def test_text_search(joint_fixture: JointFixture):
    """Test basic text search"""
    results_text = await joint_fixture.handle_query(
        class_name=CLASS_NAME, query="poolside"
    )

    assert results_text.count == 1
    assert results_text.hits[0].id_ == "1HotelAlpha-id"


async def test_filters_work(joint_fixture: JointFixture):
    """Test a query with filters selected but no query string"""
    results_filtered = await joint_fixture.handle_query(
        class_name=CLASS_NAME,
        filters=[models.Filter(key="city", value="Amsterdam")],
    )

    assert results_filtered.count == 1
    assert results_filtered.hits[0].id_ == "3zoo-id"

    results_multi_filter = await joint_fixture.handle_query(
        class_name=CLASS_NAME,
        filters=[
            models.Filter(key="category", value="hotel"),
            models.Filter(key="object.type", value="piano"),
        ],
    )

    assert results_multi_filter.count == 1
    assert results_multi_filter.hits[0].id_ == "1HotelAlpha-id"


async def test_facets_returned(joint_fixture: JointFixture):
    """Verify that facet fields are returned correctly"""
    results_faceted = await joint_fixture.handle_query(
        class_name=CLASS_NAME,
        filters=[models.Filter(key="category", value="hotel")],
    )

    config = get_config()
    facets: list[models.FieldLabel] = config.searchable_classes[
        "NestedData"
    ].facetable_fields
    facet_key_to_name = {
        x.key: x.name or x.key.replace(".", " ").title() for x in facets
    }

    for facet in results_faceted.facets:
        assert facet.key in facet_key_to_name
        assert facet.name == facet_key_to_name[facet.key]
        if facet.key == "category":
            hotel_options = [x for x in facet.options if x.value == "hotel"]
            assert len(hotel_options) == 1
            assert hotel_options[0].count == 2
        elif facet.key == "city":
            miami_options = [x for x in facet.options if x.value == "Miami"]
            assert len(miami_options) == 1
            assert miami_options[0].count == 1

            denver_options = [x for x in facet.options if x.value == "Denver"]
            assert len(denver_options) == 1
            assert denver_options[0].count == 1
        else:
            assert len(facet.options) == 2

            piano_options = [x for x in facet.options if x.value == "piano"]
            assert len(piano_options) == 1
            assert piano_options[0].count == 1

            kitchen_options = [x for x in facet.options if x.value == "kitchen"]
            assert len(kitchen_options) == 1
            assert kitchen_options[0].count == 1


async def test_limit_parameter(joint_fixture: JointFixture):
    """Test that the limit parameter works"""
    results_limited = await joint_fixture.handle_query(class_name=CLASS_NAME, limit=2)
    assert len(results_limited.hits) == 2


async def test_skip_parameter(joint_fixture: JointFixture):
    """Test that the skip parameter works"""
    results_skip = await joint_fixture.handle_query(class_name=CLASS_NAME, skip=1)
    assert len(results_skip.hits) == 2
    assert [x.id_ for x in results_skip.hits] == ["2HotelBeta-id", "3zoo-id"]


async def test_all_parameters(joint_fixture: JointFixture):
    """Sanity check - make sure it all works together"""
    results_all = await joint_fixture.handle_query(
        class_name=CLASS_NAME,
        query="hotel",
        filters=[models.Filter(key="category", value="hotel")],
        skip=1,
        limit=1,
    )

    assert len(results_all.hits) == 1
    assert results_all.hits[0].id_ == "2HotelBeta-id"


async def test_resource_load(joint_fixture: JointFixture):
    """Test the load function in the query handler"""
    # get all the documents in the collection
    results_all = await joint_fixture.handle_query(class_name=CLASS_NAME)

    content: dict = {
        "object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
        "city": "something",
        "category": "test object",
    }

    # define and load a new resource
    resource = models.Resource(id_="added-resource", content=content)

    await joint_fixture.load_resource(resource=resource, class_name=CLASS_NAME)

    # make sure the new resource is added to the collection
    results_after_load = await joint_fixture.handle_query(class_name=CLASS_NAME)
    assert results_after_load.count - results_all.count == 1

    target_search = await joint_fixture.handle_query(
        class_name=CLASS_NAME,
        query="added-resource",
        limit=0,
    )
    assert len(target_search.hits) == 1
    validated_resource = target_search.hits[0]
    assert validated_resource.id_ == resource.id_

    # remove unselected fields
    content = resource.content  # type: ignore
    del content["city"]
    del content["category"]
    del content["object"]["id"]

    assert validated_resource.content == content


async def test_loading_non_configured_resource(joint_fixture: JointFixture):
    """Test that we get the right warning for loading a non-configured class_name"""
    # define and load a new resource
    resource = models.Resource(
        id_="added-resource",
        content={
            "object": {"type": "added-resource-object", "id": "4-added"},
            "city": "something",
            "category": "test object",
            "type": "added",
        },
    )

    with pytest.raises(QueryHandlerPort.ClassNotConfiguredError):
        await joint_fixture.load_resource(resource=resource, class_name="ThisWillBreak")


async def test_missing_fields_are_ignored(joint_fixture: JointFixture):
    """Make sure we do not get an error if fields are missing from some resource"""
    results = await joint_fixture.handle_query(class_name=CLASS_NAME)
    count = results.count

    # define and load a new resource missing the "city" facet
    # and missing the top level type field, which is selected but not a facet
    resource = models.Resource(
        id_="added-resource",
        content={
            "object": {
                "type": "spurious",
                "id": "added-object",
            },
            "added-field": True,
        },
    )
    await joint_fixture.load_resource(resource=resource, class_name=CLASS_NAME)

    # this should still return all valid facets
    results = await joint_fixture.handle_query(class_name=CLASS_NAME)
    facets = results.facets
    assert len(facets) == 3
    assert facets[1].key == "city"
    assert len(facets[1].options) == 3

    # and the malformed resource should still be in the results
    assert results.count == count + 1
    for resource in results.hits:
        if resource.id_ == "added-resource":
            assert resource.content == {"object": {"type": "spurious"}}
            break
    else:
        assert False, "the added resource was not returned"


async def test_absent_resource(joint_fixture: JointFixture):
    """Make sure we get an error when looking for a resource type that doesn't exist"""
    with pytest.raises(QueryHandlerPort.ClassNotConfiguredError):
        await joint_fixture.handle_query(class_name="does_not_exist")


async def test_resource_deletion(joint_fixture: JointFixture):
    """Make sure we can delete a resource.

    Verify that the targeted resource is deleted and nothing else.
    """
    all_resources = await joint_fixture.handle_query(class_name=CLASS_NAME)

    assert all_resources.count > 1
    await joint_fixture.delete_resource(
        resource_id="1HotelAlpha-id", class_name=CLASS_NAME
    )

    # see if deletion occurred, and make sure only one item was deleted
    results_after_deletion = await joint_fixture.handle_query(class_name=CLASS_NAME)
    assert all_resources.count - results_after_deletion.count == 1

    # make extra sure the resource that got deleted was the correct one
    for resource in results_after_deletion.hits:
        assert resource.id_ != "1HotelAlpha-id"


async def test_resource_deletion_failure(joint_fixture: JointFixture):
    """Test for correct error when failing to delete a resource"""
    all_resources = await joint_fixture.handle_query(class_name=CLASS_NAME)

    assert all_resources.count > 0

    # try to delete a resource that doesn't exist
    with pytest.raises(QueryHandlerPort.ResourceNotFoundError):
        await joint_fixture.delete_resource(
            resource_id="not-here", class_name=CLASS_NAME
        )

    # verify that nothing was actually deleted
    all_resources_again = await joint_fixture.handle_query(class_name=CLASS_NAME)

    assert all_resources_again.count == all_resources.count


async def test_resource_deletion_not_configured(joint_fixture: JointFixture):
    """Test for correct error when trying to delete a non-configured resource"""
    with pytest.raises(QueryHandlerPort.ClassNotConfiguredError):
        await joint_fixture.delete_resource(
            resource_id="1HotelAlpha-id", class_name="Not-Configured"
        )
