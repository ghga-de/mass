[![tests](https://github.com/ghga-de/mass/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/mass/actions/workflows/tests.yaml)
[![Coverage Status](https://coveralls.io/repos/github/ghga-de/mass/badge.svg?branch=main)](https://coveralls.io/github/ghga-de/mass?branch=main)

# Mass

Metadata Artifact Search Service  - A service for searching metadata artifacts and filtering results.

## Description

The Metadata Artifact Search Service uses search parameters to look for metadata.

### Quick Overview of API
There are two available API endpoints that follow the RPC pattern (not REST):
One endpoint ("GET /rpc/search-options") will return an overview of all metadata classes that can be targeted
by a search. The actual search endpoint ("POST /rpc/search") can be used to search for these target classes using keywords. Hits will be reported in the context of the selected target class.
This means that target classes will be reported that match the specified search query,
however, the target class might contain embedded other classes and the match might
occur in these embedded classes, too.

Along with the hits, facet options are reported that can be used to filter down the hits by
performing the same search query again but with specific facet selections being set.

The search endpoint supports pagination to deal with large hit lists. Facet options can
help avoid having to rely on this feature by filtering down the number of hits to a single page.

For more information see the OpenAPI spec linked below.


## Installation

We recommend using the provided Docker container.

A pre-build version is available at [docker hub](https://hub.docker.com/repository/docker/ghga/mass):
```bash
docker pull ghga/mass:2.1.0
```

Or you can build the container yourself from the [`./Dockerfile`](./Dockerfile):
```bash
# Execute in the repo's root dir:
docker build -t ghga/mass:2.1.0 .
```

For production-ready deployment, we recommend using Kubernetes, however,
for simple use cases, you could execute the service using docker
on a single server:
```bash
# The entrypoint is preconfigured:
docker run -p 8080:8080 ghga/mass:2.1.0 --help
```

If you prefer not to use containers, you may install the service from source:
```bash
# Execute in the repo's root dir:
pip install .

# To run the service:
mass --help
```

## Configuration

### Parameters

The service requires the following configuration parameters:
- **`log_level`** *(string)*: The minimum log level to capture. Must be one of: `["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]`. Default: `"INFO"`.

- **`service_name`** *(string)*: Default: `"mass"`.

- **`service_instance_id`** *(string)*: A string that uniquely identifies this instance across all instances of this service. A globally unique Kafka client ID will be created by concatenating the service_name and the service_instance_id.


  Examples:

  ```json
  "germany-bw-instance-001"
  ```


- **`log_format`**: If set, will replace JSON formatting with the specified string format. If not set, has no effect. In addition to the standard attributes, the following can also be specified: timestamp, service, instance, level, correlation_id, and details. Default: `null`.

  - **Any of**

    - *string*

    - *null*


  Examples:

  ```json
  "%(timestamp)s - %(service)s - %(level)s - %(message)s"
  ```


  ```json
  "%(asctime)s - Severity: %(levelno)s - %(msg)s"
  ```


- **`log_traceback`** *(boolean)*: Whether to include exception tracebacks in log messages. Default: `true`.

- **`searchable_classes`** *(object)*: A collection of searchable_classes with facetable properties. Can contain additional properties.

  - **Additional properties**: Refer to *[#/$defs/SearchableClass](#%24defs/SearchableClass)*.

- **`resource_change_event_topic`** *(string)*: Name of the event topic used to track resource deletion and upsertion events.


  Examples:

  ```json
  "searchable_resource"
  ```


- **`resource_deletion_event_type`** *(string)*: The type to use for events with deletion instructions.


  Examples:

  ```json
  "searchable_resource_deleted"
  ```


- **`resource_upsertion_event_type`** *(string)*: The type to use for events with upsert instructions.


  Examples:

  ```json
  "searchable_resource_upserted"
  ```


- **`kafka_servers`** *(array)*: A list of connection strings to connect to Kafka bootstrap servers.

  - **Items** *(string)*


  Examples:

  ```json
  [
      "localhost:9092"
  ]
  ```


- **`kafka_security_protocol`** *(string)*: Protocol used to communicate with brokers. Valid values are: PLAINTEXT, SSL. Must be one of: `["PLAINTEXT", "SSL"]`. Default: `"PLAINTEXT"`.

- **`kafka_ssl_cafile`** *(string)*: Certificate Authority file path containing certificates used to sign broker certificates. If a CA is not specified, the default system CA will be used if found by OpenSSL. Default: `""`.

- **`kafka_ssl_certfile`** *(string)*: Optional filename of client certificate, as well as any CA certificates needed to establish the certificate's authenticity. Default: `""`.

- **`kafka_ssl_keyfile`** *(string)*: Optional filename containing the client private key. Default: `""`.

- **`kafka_ssl_password`** *(string, format: password)*: Optional password to be used for the client private key. Default: `""`.

- **`generate_correlation_id`** *(boolean)*: A flag, which, if False, will result in an error when inbound requests don't possess a correlation ID. If True, requests without a correlation ID will be assigned a newly generated ID in the correlation ID middleware function. Default: `true`.


  Examples:

  ```json
  true
  ```


  ```json
  false
  ```


- **`kafka_max_message_size`** *(integer)*: The largest message size that can be transmitted, in bytes. Only services that have a need to send/receive larger messages should set this. Exclusive minimum: `0`. Default: `1048576`.


  Examples:

  ```json
  1048576
  ```


  ```json
  16777216
  ```


- **`db_connection_str`** *(string, format: password)*: MongoDB connection string. Might include credentials. For more information see: https://naiveskill.com/mongodb-connection-string/.


  Examples:

  ```json
  "mongodb://localhost:27017"
  ```


- **`db_name`** *(string)*: Name of the database located on the MongoDB server.


  Examples:

  ```json
  "my-database"
  ```


- **`host`** *(string)*: IP of the host. Default: `"127.0.0.1"`.

- **`port`** *(integer)*: Port to expose the server on the specified host. Default: `8080`.

- **`auto_reload`** *(boolean)*: A development feature. Set to `True` to automatically reload the server upon code changes. Default: `false`.

- **`workers`** *(integer)*: Number of workers processes to run. Default: `1`.

- **`api_root_path`** *(string)*: Root path at which the API is reachable. This is relative to the specified host and port. Default: `""`.

- **`openapi_url`** *(string)*: Path to get the openapi specification in JSON format. This is relative to the specified host and port. Default: `"/openapi.json"`.

- **`docs_url`** *(string)*: Path to host the swagger documentation. This is relative to the specified host and port. Default: `"/docs"`.

- **`cors_allowed_origins`**: A list of origins that should be permitted to make cross-origin requests. By default, cross-origin requests are not allowed. You can use ['*'] to allow any origin. Default: `null`.

  - **Any of**

    - *array*

      - **Items** *(string)*

    - *null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- **`cors_allow_credentials`**: Indicate that cookies should be supported for cross-origin requests. Defaults to False. Also, cors_allowed_origins cannot be set to ['*'] for credentials to be allowed. The origins must be explicitly specified. Default: `null`.

  - **Any of**

    - *boolean*

    - *null*


  Examples:

  ```json
  [
      "https://example.org",
      "https://www.example.org"
  ]
  ```


- **`cors_allowed_methods`**: A list of HTTP methods that should be allowed for cross-origin requests. Defaults to ['GET']. You can use ['*'] to allow all standard methods. Default: `null`.

  - **Any of**

    - *array*

      - **Items** *(string)*

    - *null*


  Examples:

  ```json
  [
      "*"
  ]
  ```


- **`cors_allowed_headers`**: A list of HTTP request headers that should be supported for cross-origin requests. Defaults to []. You can use ['*'] to allow all headers. The Accept, Accept-Language, Content-Language and Content-Type headers are always allowed for CORS requests. Default: `null`.

  - **Any of**

    - *array*

      - **Items** *(string)*

    - *null*


  Examples:

  ```json
  []
  ```


## Definitions


- <a id="%24defs/FacetLabel"></a>**`FacetLabel`** *(object)*: Contains the key and corresponding user-friendly name for a facet.

  - **`key`** *(string, required)*: The raw facet key, such as study.type.

  - **`name`** *(string)*: The user-friendly name for the facet. Default: `""`.

- <a id="%24defs/SearchableClass"></a>**`SearchableClass`** *(object)*: Represents a searchable artifact or resource type.

  - **`description`** *(string, required)*: A brief description of the resource type.

  - **`facetable_properties`** *(array, required)*: A list of of the facetable properties for the resource type.

    - **Items**: Refer to *[#/$defs/FacetLabel](#%24defs/FacetLabel)*.


### Usage:

A template YAML for configurating the service can be found at
[`./example-config.yaml`](./example-config.yaml).
Please adapt it, rename it to `.mass.yaml`, and place it into one of the following locations:
- in the current working directory were you are execute the service (on unix: `./.mass.yaml`)
- in your home directory (on unix: `~/.mass.yaml`)

The config yaml will be automatically parsed by the service.

**Important: If you are using containers, the locations refer to paths within the container.**

All parameters mentioned in the [`./example-config.yaml`](./example-config.yaml)
could also be set using environment variables or file secrets.

For naming the environment variables, just prefix the parameter name with `mass_`,
e.g. for the `host` set an environment variable named `mass_host`
(you may use both upper or lower cases, however, it is standard to define all env
variables in upper cases).

To using file secrets please refer to the
[corresponding section](https://pydantic-docs.helpmanual.io/usage/settings/#secret-support)
of the pydantic documentation.

## HTTP API
An OpenAPI specification for this service can be found [here](./openapi.yaml).

## Architecture and Design:
This is a Python-based service following the Triple Hexagonal Architecture pattern.
It uses protocol/provider pairs and dependency injection mechanisms provided by the
[hexkit](https://github.com/ghga-de/hexkit) library.

This service is currently designed to work with MongoDB and uses an aggregation pipeline to produce search results.

Typical sequence of events is as follows:
1. Requests are received by the API, then directed to the QueryHandler in the core.

2. From there, the configuration is consulted to retrieve any facetable properties for the searched resource class.

3. The search parameters and facet fields are passed to the Aggregator, which builds and runs the aggregation pipeline on the appropriate collection. The aggregation pipeline is a series of stages run in sequence:
   - The first stage runs a text match using the query string.
   - The second stage applies a sort based on the IDs.
   - The third stage applies any filters supplied in the search parameters.
   - The fourth stage extract facets.
   - The fifth/final stage transforms the results structure into {facets, hits, hit count}.
4. Once retrieved in the Aggregator, the results are passed back to the QueryHandler where they are shoved into a QueryResults pydantic model for validation before finally being sent back to the API.


## Development

For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of VS Code
in combination with Docker Compose.

To use it, you have to have Docker Compose as well as VS Code with its "Remote - Containers"
extension (`ms-vscode-remote.remote-containers`) installed.
Then open this repository in VS Code and run the command
`Remote-Containers: Reopen in Container` from the VS Code "Command Palette".

This will give you a full-fledged, pre-configured development environment including:
- infrastructural dependencies of the service (databases, etc.)
- all relevant VS Code extensions pre-installed
- pre-configured linting and auto-formatting
- a pre-configured debugger
- automatic license-header insertion

Moreover, inside the devcontainer, a convenience commands `dev_install` is available.
It installs the service with all development dependencies, installs pre-commit.

The installation is performed automatically when you build the devcontainer. However,
if you update dependencies in the [`./pyproject.toml`](./pyproject.toml) or the
[`./requirements-dev.txt`](./requirements-dev.txt), please run it again.

## License

This repository is free to use and modify according to the
[Apache 2.0 License](./LICENSE).

## README Generation

This README file is auto-generated, please see [`readme_generation.md`](./readme_generation.md)
for details.
