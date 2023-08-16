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
"""Top-level functionality for the microservice"""
from fastapi import FastAPI
from ghga_service_commons.api import configure_app, run_server
from pymongo import TEXT, MongoClient

from mass.adapters.inbound.fastapi_.routes import router
from mass.config import Config
from mass.container import Container


def collection_init_and_index_creation(config: Config):
    """Creates `MongoDB` collections and indexes.

    Creates collections for all configured classes in `searchable_classes` if they don't
    already exist. At the same time, it will also create the text index if it doesn't
    already exist. This is primarily needed because the text index has to exist in order
    to perform query string searches.
    """

    # get client
    client = MongoClient(config.db_connection_str.get_secret_value())
    db = client[config.db_name]

    expected_collections = list(config.searchable_classes.keys())
    existing_collections = db.list_collection_names()

    # loop through configured classes (i.e. the expected collection names)
    for collection_name in expected_collections:
        if collection_name not in existing_collections:
            db.create_collection(collection_name)
        collection = db[collection_name]

        # see if the wildcard text index exists and add it if not
        wildcard_text_index_exists = any(
            index["key"] == {"$**": "text"} for index in collection.list_indexes()
        )

        if not wildcard_text_index_exists:
            collection.create_index([("$**", TEXT)])


def get_configured_container(*, config: Config) -> Container:
    """Create and configure a DI container."""

    container = Container()
    container.config.load_config(config)
    container.wire(modules=["mass.adapters.inbound.fastapi_.routes"])

    return container


def get_rest_api(*, config: Config) -> FastAPI:
    """
    Creates a FastAPI app.
    For full functionality of the api, run in the context of a CI container with
    correct wiring and initialized resources (see the run_api function below).
    """

    api = FastAPI()
    api.include_router(router=router)
    configure_app(api, config=config)
    return api


async def run_rest():
    """Run the server"""
    config = Config()

    async with get_configured_container(config=config):
        api = get_rest_api(config=config)
        await run_server(app=api, config=config)


async def consume_events(run_forever: bool = True):
    """Run the event consumer"""

    config = Config()

    async with get_configured_container(config=config) as container:
        event_subscriber = await container.event_subscriber()
        await event_subscriber.run(forever=run_forever)
