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

"""ResourceDao Port and DaoCollectionPort"""
from abc import ABC, abstractmethod

from hexkit.protocols.dao import DaoNaturalId
from typing_extensions import TypeAlias

from mass.core.models import Resource

ResourceDaoPort: TypeAlias = DaoNaturalId[Resource]


class DaoCollectionPort(ABC):
    """Port for a DAO collection object"""

    @abstractmethod
    def get_dao(self, *, class_name: str) -> ResourceDaoPort:
        """Retrieve a ResourceDaoPort for the specified resource class name

        Args:
            class_name (str): name of the resource class

        Returns:
            A DAO for the specified resource (ResourceDaoPort)
        """
        ...
