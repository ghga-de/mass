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

"""Contains the ResourceDaoCollection, which houses a DAO for each resource class"""
from hexkit.protocols.dao import DaoFactoryProtocol
from pymongo import TEXT, MongoClient

from mass.config import Config
from mass.core import models
from mass.ports.outbound.dao import DaoCollectionPort, ResourceDao


class DaoNotFoundError(RuntimeError):
    """Raised when a DAO is not found."""

    def __init__(self, class_name: str):
        super().__init__(f"Could not find DAO for class '{class_name}'.")


class DaoCollection(DaoCollectionPort):
    """Provides a DAO for each configured searchable resource class"""

    @classmethod
    async def construct(
        cls,
        dao_factory: DaoFactoryProtocol,
        config: Config,
    ):
        """Initialize the DAO collection with one DAO for each resource class"""
        resource_daos: dict[str, ResourceDao] = {}
        for name in config.searchable_classes.keys():
            resource_daos[name] = await dao_factory.get_dao(
                name=name, dto_model=models.Resource, id_field="id_"
            )

        return cls(config=config, resource_daos=resource_daos)

    def __init__(
        self,
        config: Config,
        resource_daos: dict[str, ResourceDao],
    ):
        """Initialize the collection of DAOs"""
        self._config = config
        self._resource_daos = resource_daos

    def get_dao(self, *, class_name: str) -> ResourceDao:
        """returns a dao for the given resource class name

        Raises:
            DaoNotFoundError: if the DAO isn't found
        """
        try:
            return self._resource_daos[class_name]
        except KeyError as err:
            raise DaoNotFoundError(class_name=class_name) from err

    def collection_init_and_index_creation(self) -> None:
        # get client
        client: MongoClient = MongoClient(
            self._config.db_connection_str.get_secret_value()
        )
        db = client[self._config.db_name]

        expected_collections = list(self._config.searchable_classes)
        existing_collections = db.list_collection_names()

        # loop through configured classes (i.e. the expected collection names)
        for collection_name in expected_collections:
            if collection_name not in existing_collections:
                db.create_collection(collection_name)
            collection = db[collection_name]

            # see if the wildcard text index exists and add it if not
            wildcard_text_index_exists = any(
                index["name"] == f"$**_{TEXT}" for index in collection.list_indexes()
            )

            if not wildcard_text_index_exists:
                collection.create_index([("$**", TEXT)])
