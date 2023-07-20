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

"""Provides multiple fixtures in one spot, with a mongodb fixture that comes pre-populated"""
# pylint: disable=unused-import, redefined-outer-name

import glob
import re
from dataclasses import dataclass
from typing import AsyncGenerator

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    MongoDbFixture,
    get_mongodb_fixture,
)
from pymongo import TEXT

from mass.config import Config
from mass.container import Container
from mass.main import get_configured_container, get_rest_api
from tests.fixtures.config import get_config
from tests.fixtures.utils import get_resources_from_file


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    container: Container
    mongodb: MongoDbFixture
    rest_client: AsyncTestClient

    def reset_state(self):
        """Delete everything in the database to start from a clean slate"""
        self.mongodb.empty_collections()

    def load_test_data(self):
        """Populate a collection for each file in test_data"""
        filename_pattern = re.compile(r"/(\w+)\.json")
        for filename in glob.glob("tests/fixtures/test_data/*.json"):
            match_obj = re.search(filename_pattern, filename)
            if match_obj:
                collection_name = match_obj.groups()[0]
                resources = get_resources_from_file(filename)
                self.mongodb.client[self.config.db_name][collection_name].insert_many(
                    resources
                )
                self.mongodb.client[self.config.db_name][collection_name].create_index(
                    keys=[("$**", TEXT)]
                )


@pytest_asyncio.fixture
async def joint_fixture(
    mongodb_fixture: MongoDbFixture,  # noqa: F811
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""

    # merge configs from different sources with the default one:
    config = get_config(sources=[mongodb_fixture.config])

    # create a DI container instance:translators
    async with get_configured_container(config=config) as container:
        container.wire(modules=["mass.adapters.inbound.fastapi_.routes"])

        # setup an API test client:
        api = get_rest_api(config=config)
        async with AsyncTestClient(app=api) as rest_client:
            yield JointFixture(
                config=config,
                container=container,
                mongodb=mongodb_fixture,
                rest_client=rest_client,
            )


mongodb_fixture = get_mongodb_fixture()
