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
"""Tests concerning the sorting functionality"""

import pytest
from hexkit.custom_types import JsonObject

from mass.core import models
from tests.fixtures.joint import JointFixture

CLASS_NAME = "SortingTests"
BASIC_SORT_PARAMETERS = [
    models.SortingParameter(sort_field="id_", sort_order=models.SortOrder.ASCENDING)
]


def sort_resources(
    resources: list[models.Resource], sorts: list[models.SortingParameter]
) -> list[models.Resource]:
    """Convenience function to sort a list of resources for comparison"""
    sorted_list = resources.copy()

    for parameter in sorts:
        reverse = True if parameter.sort_order == -1 else False

        if parameter.sort_field == "id_":
            sorted_list.sort(key=lambda resource: resource.id_, reverse=reverse)
        else:
            # all other fields will be contained within 'content'.
            sorted_list.sort(
                key=lambda resource: resource.dict()["content"][parameter.sort_field],
                reverse=reverse,
            )

    return sorted_list


@pytest.mark.asyncio
async def test_api_without_search_parameters(joint_fixture: JointFixture):
    """Make sure default Pydantic model parameter works as expected"""

    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
    }

    results = await joint_fixture.call_search_endpoint(
        search_parameters=search_parameters
    )
    assert results.count >= 0
    expected = sort_resources(results.hits, BASIC_SORT_PARAMETERS)
    assert results.hits == expected


@pytest.mark.asyncio
async def test_sort_with_id_not_last(joint_fixture: JointFixture):
    """Test sorting parameters that contain id_, but id_ is not final sorting field.

    Since we modify sorting parameters based on presence of id_, make sure there aren't
    any bugs that will break the sort or query process.
    """
    sorts = [
        {"sort_field": "id_", "sort_order": 1},
        {"sort_field": "field", "sort_order": -1},
    ]
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": sorts,
    }

    sorts_in_model_form = [models.SortingParameter(**param) for param in sorts]
    results = await joint_fixture.call_search_endpoint(search_parameters)
    assert results.hits == sort_resources(results.hits, sorts_in_model_form)


@pytest.mark.asyncio
async def test_sort_with_params_but_not_id(joint_fixture: JointFixture):
    """Test supplying sorting parameters but omitting id_.

    In order to provide consistent sorting, id_ should always be included. If it's not
    explicitly included, it will be added as the final sorting field in order to break
    any tie between otherwise equivalent keys. If it is included but is not the final
    field, then we should not modify the parameters.
    """
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [{"sort_field": "field", "sort_order": 1}],
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    assert results.hits == sort_resources(results.hits, BASIC_SORT_PARAMETERS)


@pytest.mark.asyncio
async def test_sort_with_invalid_field(joint_fixture: JointFixture):
    """Test supplying an invalid field name as a sort field.

    MongoDB treats any documents without a given sort field as if they had a `null`
    value for it. If we sort with a truly invalid field, it should have no impact on the
    resulting sort order.
    """

    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [{"sort_field": "some_bogus_field", "sort_order": 1}],
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    assert results.hits == sort_resources(results.hits, BASIC_SORT_PARAMETERS)


@pytest.mark.parametrize("sort_order", [-7, 17, "some_string"])
@pytest.mark.asyncio
async def test_sort_with_invalid_sort_order(joint_fixture: JointFixture, sort_order):
    """Test supplying an invalid value for the sort order"""
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [{"sort_field": "field", "sort_order": sort_order}],
    }

    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sort_with_invalid_field_and_sort_order(joint_fixture: JointFixture):
    """Test with both invalid field name and invalid sort order."""
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [{"sort_field": "some_bogus_field", "sort_order": -7}],
    }

    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sort_with_duplicate_field(joint_fixture: JointFixture):
    """Supply sorting parameters with two instances of the same sort field.

    This should be prevented by the pydantic model validator and raise an HTTP error.
    """
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [
            {"sort_field": "field", "sort_order": 1},
            {"sort_field": "field", "sort_order": 1},
        ],
    }
    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 422
