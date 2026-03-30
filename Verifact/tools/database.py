import google.auth
import os

import google.oauth2.service_account as service_account

from pathlib import Path
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode
from dotenv import load_dotenv

base_dir = Path(__file__).resolve().parent.parent.parent
env_path = base_dir / ".env.local"

load_dotenv(dotenv_path=env_path)

try:
    credentials, _ = google.auth.default()
except google.auth.exceptions.DefaultCredentialsError:
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path:
        raise EnvironmentError(
            "No ADC credentials found and GOOGLE_APPLICATION_CREDENTIALS is not set in .env.local"
        )
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    
big_query_tools = BigQueryToolset(
    credentials_config=BigQueryCredentialsConfig(credentials=credentials),
    bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED),
    tool_filter=[
        "list_dataset_ids",
        "get_dataset_info",
        "list_table_ids",
        "get_table_info",
        "execute_sql",
        "ask_data_insights",
    ],
)
