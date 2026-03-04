# CPS AI Dispro Backend

## Overview

This is the backend app for document processing and AI analysis.

## Requirements

`azure-cli` 2.75 or newer.

```shell
az --version
```

Python 3.11 with pip 24.2 or newer

```shell
# on unix
python3 --version
pip3 --version
# on windows
py --version
py -m pip --version
```

Azure Function Tool 4.0 or newer 
```shell
func --version
```

## 🔧 Deployment Steps

### Navigate to the code source directory

```shell
cd path/to/back
```

### Create an environment file

```shell
cp env.template .env
```

Open the file in your preferred text editor and populate the values.

### Evaluate dependencies

```shell
(ls .env && echo 'INFO: Found .env') || echo 'CRITICAL: Missing .env'
(ls requirements.txt && echo 'INFO: Found requirements.txt') || echo 'CRITICAL: Missing requirements.txt'
(ls requirements-dev.txt && echo 'INFO: Found requirements-dev.txt') || echo 'CRITICAL: Missing requirements-dev.txt'
```

### Create Python environment and install dependencies

```shell
# on unix
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements-dev.txt
# on windows
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install -r requirements-dev.txt
```

### Test Locally

Tests under `tests` directory use SQLite in-memory database.

```shell
# Run all tests
pytest

# Optionally use `-v` for verbose, `-vv` for very verbose, `-s` and standard output, and `--durations=#` to show the # slowest  calls/setups
pytest -vv -s --durations=10

# Run with coverage
pytest --cov=src --cov-report=html

# Run all local tests
pytest tests/

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::test_create_case -v

# Run all integration tests marked with 'integration'
pytest integration/ -v -m integration
```

## Local Deployment

```shell
# ensure venv is activated then start local server
func start --verbose
```

## Zip Deployment on Windows

```shell
# Select files to add to zip
$files = Get-ChildItem -Path "." -Exclude ".venv","__pycache__",".github",".pytest_cache",".tmp",".vscode","htmlcov",".env",".coverage"
# Create zipped file
mkdir -p .deployment
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
Compress-Archive -Path $files -DestinationPath ".deployment/fa_$timestamp.zip" -CompressionLevel "Optimal"
# Sign in to azure account
az login
# Deploy the zip file to Azure Function App
az functionapp deployment source config-zip --resource-group {RESOURCE_GROUP} --name {FUNCTION_APP_NAME} --src ".deployment/fa_$timestamp.zip"
```

### Request Examples

`GET /ping`

expected response:
* HTTP response code: `200 OK`
* HTTP response content: `pong`

`GET /health`

expected response:
* HTTP response code: `200 OK`
* HTTP response content: `{"status": "success"}`

`GET /health?route={service_name}`
where `service_name` is `blob`, `postgres`, `llm`, `docintel`, `keyvault`, or `cms`

expected response:
* HTTP response code: `200 OK`
* HTTP response content: `{"status": "success", "{service_name}": "connected ({service_specific_output})"}`

`POST /ingest`

request body for CMS as datasource
```json
{
    "trigger_type": "urn", 
    "value": "16XN1001318",
    "experiment_id": "TST"
}
```

request body for Azure Blob Storage as datasource 
```json
{
    "trigger_type": "blob_name", 
    "value": "test_small.docx",
    "experiment_id": "TST"
}
```


`POST /analyse`

request body
```json
{ 
    "section_id": 141,
    "task_ids": ["tst-theme-01"]
}
```


## Troubleshooting

**Local tests fail?**
Ensure .env is populated.

**Connection to PostgreSQL fails?**
1. Verify Azure PostgreSQL is running
2. Check firewall rules allow your IP
3. Verify credentials are correct
4. [Optionally] Test with psql: `psql -h your-server.postgres.database.azure.com -U pgadmin`

## Contributing

1. **Always use context managers** for sessions
2. **Use repositories** instead of direct ORM queries
3. **Run tests with SQLite** in-memory for fast, isolated tests before committing
4. **Run tests with deployed PostgreSQL** for integration testing before merging.
5. **Monitor with health checks** in Azure Functions
6. **Let auto-create** handle schema on first cold start