# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Defines dataclasses for holding business-logic data"""

from enum import Enum

from hexkit.custom_types import JsonObject
from pydantic import BaseModel, Field


class FieldLabel(BaseModel):
    """Contains the key and corresponding user-friendly name for a field"""

    key: str = Field(..., description="The raw field key, such as study.type")
    name: str = Field(default="", description="The user-friendly name for the field")


class FacetOption(BaseModel):
    """Represents the format for an option for a facet"""

    value: str = Field(..., description="The text value of the facet option")
    count: int = Field(..., description="The number of results matching the facet")


class Facet(FieldLabel):
    """Represents a facet's key, name, and the discovered options for the facet"""

    options: list[FacetOption] = Field(
        ..., description="The list of options for the facet"
    )


class SearchableClass(BaseModel):
    """Represents a searchable artifact or resource type"""

    description: str = Field(
        ..., description="A brief description of the resource type"
    )
    facetable_fields: list[FieldLabel] = Field(
        [], description="A list of of the facetable fields for the resource type"
    )
    selected_fields: list[FieldLabel] = Field(
        [], description="A list of the returned fields for the resource type"
    )


class Resource(BaseModel):
    """Represents an artifact or resource class such as a Dataset, Sample, Study, etc."""

    id_: str = Field(..., description="The identifier for this resource")
    content: JsonObject = Field(..., description="The actual content of the resource")


class Filter(BaseModel):
    """Represents a filter used to refine results"""

    key: str = Field(..., description="The field to filter")
    value: str = Field(..., description="The value the field must match")


class QueryResults(BaseModel):
    """Contains the facets, hit count, and hits"""

    facets: list[Facet] = Field(default=[], description="Contains the faceted fields")
    count: int = Field(default=0, description="The number of results found")
    hits: list[Resource] = Field(default=[], description="The search results")


class SortOrder(Enum):
    """Represents the possible sorting orders"""

    ASCENDING = "ascending"
    DESCENDING = "descending"
    RELEVANCE = "relevance"


class SortingParameter(BaseModel):
    """Represents a combination of a field to sort and the sort order"""

    field: str = Field(
        ...,
        description=("Which field to sort results by."),
    )
    order: SortOrder = Field(
        default=SortOrder.ASCENDING, description="Sort order to apply to sort_field"
    )
