# Ingesteur - A Metadata-Driven Financial Data Ingestion Pipeline

## 1. Overview

Ingesteur is a robust, metadata-driven ETL pipeline designed to ingest financial market data from various sources (initially Binance) and process it through a multi-layered data lake on AWS. The entire infrastructure is defined and deployed as code using Terraform.

The core principle of this project is a **contract-driven approach**. The logic for data ingestion, validation, and transformation is not hardcoded but is defined in a series of YAML "contract" and "schema" files. This allows the pipeline to be easily extended to new data sources, tables (entities), and transformations without changing the core Python or Terraform code.

The pipeline processes data through three distinct layers in an S3 data lake:
*   **Bronze Layer**: Stores raw, untouched data from the source, serving as the single source of truth.
*   **Silver Layer**: Stores cleaned, normalized, and validated data, ready for analytics.
*   **Gold Layer**: (Future implementation) Stores aggregated, business-level data for reporting and dashboarding.

## 2. Architecture Overview

The entire infrastructure is deployed on AWS using Terraform. The architecture is designed to be scalable, event-driven, and cost-effective, leveraging serverless components where possible.

```
                               +-----------------------+
                               |    Binance API        |
                               +-----------+-----------+
                                           |
                                           | (triggered by SQS)
                                           v
+------------------+           +-----------+-----------+
| Ingestion Requester| ----> |   SQS Ingest Queue    |
| (tools/)         |         +-----------+-----------+
+------------------+                       |
                                           | 1. Trigger Lambda
                                           v
+----------------------------------------------------+   +-------------------+
| AWS S3 Data Lake (Single Bucket)                   |   | S3 Config Bucket  |
|                                                    |   | (configs/*)       |
|  +---------------------------------------------+   |   +-------------------+
|  | data/bronze/binance/trades/ (raw CSV)       |<--+---------+
|  +---------------------------------------------+   | 2. Lambda |
|                  |                                 |   (ingestion)     |
|                  | 3. S3 Put Event                 |           |
|                  v                                 |   +-------+-----------+
|  +---------------------------+                     |   |   Bronze-to-Silver|
|  |   Bronze-to-Silver Lambda   |---------------------->|   Lambda          |
|  +---------------------------+                     |   +-------------------+
|                  |                                 |
|                  | 4. Write Cleaned Parquet        |
|                  v                                 |
|  +---------------------------------------------+   |
|  | data/silver/binance/trades/ (Parquet)       |   |
|  +---------------------------------------------+   |
|                                                    |
+----------------------------------------------------+
         ^                                     ^
         | 5. Crawler updates partitions       | 6. Jobs & Lambdas update tables
         v                                     v
+----------------------+                 +------------------+
| Glue Data Catalog    | <-------------> |  Amazon Athena   |
| (Tables & Partitions)|                 +------------------+
+----------------------+
```

### Key Components:
*   **Configuration**: All pipeline logic is controlled by YAML files stored in a dedicated `config/` prefix in the data lake S3 bucket. These are deployed via the `config_publisher` tool.
*   **Data Lake**: A single S3 bucket houses all data, organized by layer, data source, and table (`data/{layer}/{dataSource}/{tableName}`).
*   **Ingestion**: A combination of a Python tool (`ingestion_requester`) and an SQS-triggered Lambda function (`ingestion-lambda`) fetches data from the source API and lands it in the Bronze layer.
*   **Bronze-to-Silver ETL**: An event-driven Lambda function is triggered by new objects in the Bronze layer. It reads the corresponding configuration, applies cleaning and validation rules, and writes the data to the Silver layer in Parquet format.
*   **Glue Data Catalog**: Acts as the central metastore for all data. Tables are created and updated programmatically by the deployment script and ETL processes. A Glue Crawler keeps the Bronze tables' partitions in sync.
*   **Terraform**: The entire infrastructure, including S3 buckets, Lambda functions, Glue jobs/crawlers, and IAM roles, is managed via Terraform modules in the `terrafom_silver/` directory.


## 3. Project Structure

The repository is organized into three main directories: `configurations`, `scripts` (inside `tools`), and `terrafom_silver`.

```
/
├── configurations/         # Local source of truth for all pipeline configurations.
│   ├── active_sources.json # Master file listing which data sources and tables are active.
│   └── binance/
│       ├── tables/         # Main configuration for each table (data paths, partitions).
│       │   └── trades.json
│       └── schemas/        # Column-level schema and validation rules for each table.
│           └── trades.json
│
├── scripts/                # Python scripts for managing and interacting with the pipeline.
│   ├── config_models.py    # Pydantic models for validating all configuration files.
│   └── deploy_configs.py   # Script to validate and upload local configs to S3.
│
├── terrafom_silver/        # All Terraform infrastructure code.
│   ├── main.tf             # Root module, defines resources and calls other modules.
│   ├── variables.tf        # Root variables for the Terraform configuration.
│   ├── glue/               # Terraform module for the Glue Crawler.
│   ├── glue_jobs/          # Terraform module for generic Glue Jobs.
│   ├── lambda/             # Terraform module for creating Lambda functions and layers.
│   ├── s3/                 # Terraform module for creating S3 buckets.
│   └── sqs/                # Terraform module for creating SQS queues.
│
├── test/                   # Unit tests for the Python tools and scripts.
│
├── request_ingestion.py    # Legacy script for sending ingestion requests.
└── requirements.txt        # Python dependencies for the project.
```

## 4. How to Use

### Prerequisites
*   Python 3.10+
*   Terraform 1.0+
*   AWS CLI, with credentials configured.
*   Docker (for local development of AWS Glue scripts).

### Setup
1.  **Install Dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

### Step 1: Define Configurations
1.  Add or modify the YAML configuration files in the `configurations/` directory.
    *   To add a new table, create its corresponding `tables/{table_name}.json` and `schemas/{table_name}.json` files under the correct data source directory (e.g., `configurations/binance/`).
2.  Ensure the new table is listed in `configurations/active_sources.json`.

### Step 2: Deploy Configurations & Bronze Tables
Run the `deploy_configs.py` script to validate your local configurations, upload them to S3, and create the necessary Bronze tables in the Glue Data Catalog.

```sh
# Replace <your-data-lake-bucket> with the name of your deployed S3 bucket
python scripts/deploy_configs.py <your-data-lake-bucket>
```

### Step 3: Run the Ingestion
The `request_ingestion.py` script sends messages to the SQS queue to trigger the ingestion Lambda. *(Note: This process can be updated to be driven by the `ingestion_config` in the new configuration files).*

```sh
python request_ingestion.py
```
This will land new data in the Bronze layer, which will automatically trigger the Bronze-to-Silver Lambda transformation.

### Step 4: Deploy Infrastructure
To apply any changes to the AWS infrastructure, run the Terraform deployment script.

```sh
cd terrafom_silver/
./terraform.sh
```

## 5. Testing
This project uses `pytest`. To run the complete suite of unit tests for the Python tools:

1.  **Install Test Dependencies**:
    ```sh
    pip install pytest pytest-mock
    ```
2.  **Run Pytest**:
    From the root directory of the project, simply run:
    ```sh
    pytest
    ```
This will automatically discover and run all test files located in the `test/` directory.
