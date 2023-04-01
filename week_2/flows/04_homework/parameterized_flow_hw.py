from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket 
from random import randint 
from prefect.tasks import task_input_hash
from datetime import timedelta


@task(retries=3)
def fetch(dataset_url: str) -> pd.DataFrame:
    """Read taxi data from web into pandas DataFrame"""
    # simulating failure to test retries
    # if randint(0, 1) == 1:
    #     raise Exception()
    df = pd.read_csv(dataset_url)
    return df

@task(log_prints=True)
def clean(df: pd.DataFrame, color: str) -> pd.DataFrame:
    """Fix some dtype issues"""
    if color == 'yellow':
        df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
        df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'])
    else:
        df['lpep_pickup_datetime'] = pd.to_datetime(df['lpep_pickup_datetime'])
        df['lpep_dropoff_datetime'] = pd.to_datetime(df['lpep_dropoff_datetime'])
    print(df.head(2))
    print(f'columns: {df.dtypes}')
    print(f'rows: {len(df)}')
    return df

@task()
def write_local(df: pd.DataFrame, color: str, dataset_file: str) -> Path:
    """Write DataFrame out locally as parquet file"""
    path = Path(f'week_2/data/{color}/{dataset_file}.parquet')
    df.to_parquet(path, compression="gzip")
    return path

@task()
def write_gcs(path: Path) -> None:
    """Upload local parquet file to GCS"""
    gcs_block = GcsBucket.load("de-week-two-example")
    gcs_block.upload_from_path(from_path=path, to_path=path)
    return

@flow()
def etl_web_to_gcs(year: int, month: int, color: str) -> None:
    """The main ETL function"""
    dataset_file = f'{color}_tripdata_{year}-{month:02}'
    dataset_url = f'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{color}/{dataset_file}.csv.gz'

    df = fetch(dataset_url)
    df_clean = clean(df, color) #add color so can fix different columns in green dataset 
    path = write_local(df, color, dataset_file)
    write_gcs(path)
    
@flow()
def etl_parent_flow(
    months: list[int] = [1], year: int = 2020, color: str = 'green'
):
    for month in months:
        etl_web_to_gcs(year, month, color)
    
if __name__ == '__main__':
    color = 'color'
    months = []
    year = 0
    etl_parent_flow(months, year, color)