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

"""Collection of tests that verify log output"""

from typing import Union

import pytest
from ghga_event_schemas.pydantic_ import (
    MetadataDatasetID,  # used for intentionally failing validation
)
from ghga_event_schemas.pydantic_ import SearchableResource, SearchableResourceInfo

from mass.adapters.inbound.event_sub import (
    CLASS_NOT_CONFIGURED_LOG_MSG,
    DELETION_FAILED_LOG_MSG,
    SCHEMA_VALIDATION_ERROR_LOG_MSG,
)
from tests.fixtures.joint import JointFixture

BAD_ACCESSION = "badaccession"
BAD_CLASS_NAME = "badclassname"
BAD_CLASS_NAME_DELETE = SearchableResourceInfo(
    accession="1HotelAlpha-id", class_name=BAD_CLASS_NAME
)
BAD_CLASS_NAME_UPSERT = SearchableResource(
    accession="1HotelAlpha-id", class_name=BAD_CLASS_NAME, content={}
)
BAD_ACCESSION_DELETE = SearchableResourceInfo(
    accession=BAD_ACCESSION, class_name="DatasetEmbedded"
)
UPSERT_EVENT = "upsert"
DELETE_EVENT = "delete"
WARNING_LEVEL = "WARNING"
ERROR_LEVEL = "ERROR"


@pytest.mark.parametrize(
    ("resource", "event_type", "expected_log_level", "expected_log_message"),
    [
        (
            BAD_CLASS_NAME_DELETE,
            DELETE_EVENT,
            WARNING_LEVEL,
            CLASS_NOT_CONFIGURED_LOG_MSG.replace("%s", BAD_CLASS_NAME),
        ),
        (
            BAD_CLASS_NAME_UPSERT,
            UPSERT_EVENT,
            WARNING_LEVEL,
            CLASS_NOT_CONFIGURED_LOG_MSG.replace("%s", BAD_CLASS_NAME),
        ),
        (
            MetadataDatasetID(accession="fail"),
            DELETE_EVENT,
            ERROR_LEVEL,
            SCHEMA_VALIDATION_ERROR_LOG_MSG.replace(
                "%s", SearchableResourceInfo.__name__
            ),
        ),
        (
            MetadataDatasetID(accession="fail"),
            UPSERT_EVENT,
            ERROR_LEVEL,
            SCHEMA_VALIDATION_ERROR_LOG_MSG.replace("%s", SearchableResource.__name__),
        ),
        (
            BAD_ACCESSION_DELETE,
            DELETE_EVENT,
            WARNING_LEVEL,
            DELETION_FAILED_LOG_MSG.replace("%s", BAD_ACCESSION),
        ),
    ],
    ids=[
        "Non-configured class name during deletion event",
        "Non-configured class name during upsertion evenet",
        "Schema validation failure during deletion event",
        "Schema validation failure during upsertion event",
        "Deletion failure due to non-existent accession",
    ],
)
@pytest.mark.asyncio
async def test_event_sub_logging(
    joint_fixture: JointFixture,
    caplog,
    resource: Union[SearchableResourceInfo, SearchableResource, MetadataDatasetID],
    event_type: str,
    expected_log_level: str,
    expected_log_message: str,
):
    """Test log output for different error situations when handling events in event_sub.

    This should touch all error* log situations found in the event_sub module.
    The flow here is to define an event and publish it.
    The error handling should occur when we try to consume the event, but it won't raise
    anything because we just log the activity in order to keep the event consumer alive.
    Therefore, any info in the logs is even more valuable and we should make sure that
    the logging output is correct (no copy/paste errors, for example).

    Constants are defined above in an effort to keep code redundancy down.
    """
    query_handler = await joint_fixture.container.query_handler()

    # get all the documents in the collection
    all_results = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="",
        filters=[],
    )

    assert all_results.count > 0

    event_to_use = (
        joint_fixture.config.resource_upsertion_event_type
        if event_type == "upsert"
        else joint_fixture.config.resource_deletion_event_type
    )

    await joint_fixture.kafka.publish_event(
        payload=resource.dict(),
        type_=event_to_use,
        topic=joint_fixture.config.searchable_resource_events_topic,
        key=f"dataset_embedded_{resource.accession}",
    )

    # flush any logs that might have accumulated
    caplog.clear()

    # consume the event
    consumer = await joint_fixture.container.event_subscriber()
    await consumer.run(forever=False)

    # examine logs and try to be specific by filtering by logger name
    logs_of_interest = [
        record
        for record in caplog.records
        if record.name == "mass.adapters.inbound.event_sub"
    ]
    assert len(logs_of_interest) == 1
    record = logs_of_interest[0]
    assert record.levelname == expected_log_level
    assert record.message == expected_log_message
