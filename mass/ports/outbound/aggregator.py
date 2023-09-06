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
"""Contains the outbound ports for the Aggregator and AggregatorCollection classes"""
from abc import ABC, abstractmethod
from typing import Optional

from hexkit.custom_types import JsonObject

from mass.core import models


class AggregationError(RuntimeError):
    """Raised when something goes wrong with the aggregation operation"""

    def __init__(self, aggregation_details: str):
        super().__init__(
            f"Something went wrong while aggregating with: {aggregation_details}"
        )


class AggregatorPort(ABC):
    """Describes an aggregator class, which performs aggregation ops on a mongodb collection"""

    @abstractmethod
    async def aggregate(
        self,
        *,
        query: str,
        filters: list[models.Filter],
        facet_fields: list[models.FacetLabel],
        skip: int = 0,
        limit: Optional[int] = None,
        sorting_parameters: list[models.SortingParameter],
    ) -> JsonObject:
        """Applies an aggregation pipeline to a mongodb collection"""
        ...


class AggregatorCollectionPort(ABC):
    """A port describing an AggregatorCollection object"""

    @abstractmethod
    def get_aggregator(self, *, class_name: str) -> AggregatorPort:
        """Retrieve an AggregatorPort for the specified resource class name

        Args:
            class_name (str): name of the resource class

        Returns:
            An AggregatorPort for the specified resource (AggregatorPort)
        """
        ...
