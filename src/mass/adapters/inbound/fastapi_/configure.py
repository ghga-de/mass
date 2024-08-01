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

"""Utils to configure the FastAPI app"""

from fastapi import FastAPI
from ghga_service_commons.api import configure_app

import mass
from mass.adapters.inbound.fastapi_.routes import router
from mass.config import Config


def get_configured_app(*, config: Config) -> FastAPI:
    """Create and configure a REST API application."""
    doc = mass.__doc__
    try:
        title, description = mass.__doc__.split("\n\n", 1)
    except ValueError:
        title, description = doc, ""
    title = title.strip()
    description = description.strip()
    version = mass.__version__

    app = FastAPI(title=title, description=description, version=version)
    app.include_router(router)
    configure_app(app, config=config)

    return app
