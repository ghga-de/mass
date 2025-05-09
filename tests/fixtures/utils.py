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

"""Utils for Fixture handling"""

import json
from pathlib import Path

from pydantic import BaseModel

from mass.core.models import Resource

BASE_DIR = Path(__file__).parent.resolve()


def dto_to_document(dto: BaseModel):
    """Convert a BaseModel to a mongodb-compatible document"""
    document = json.loads(dto.json())
    document["_id"] = document.pop("id_")
    return document


def get_resources_from_file(filename: str) -> list[Resource]:
    """Utility function to load resources from a file"""
    with open(filename, encoding="utf-8") as file:
        json_object = json.loads(file.read())
        resources: list[Resource] = []
        for item in json_object["items"]:
            id_ = item.pop("id_")
            resource = Resource(id_=id_, content=item)
            resources.append(resource)
        return resources
