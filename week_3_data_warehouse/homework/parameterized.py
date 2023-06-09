from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket 
from random import randint 
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(retries=3)
def fetch(dataset_url: str) -> pd.DataFrame:
    """Read tax data from web into pandas DataFrame"""
    df = pd.read_csv(dataset_url) 
    return df 

@task(log_prints=True)
def clean(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Fix dtype issues"""
    if year == 2019:
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
        df['dropOff_datetime'] = pd.to_datetime(df['dropOff_datetime'])
        df['PUlocationID'] = df['PUlocationID'].astype(float)
        df['DOlocationID'] = df['DOlocationID'].astype(float)
    else:
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
        df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'])
        df['PULocationID'] = df['PULocationID'].astype(float)
        df['DOLocationID'] = df['DOLocationID'].astype(float)
    print(df.head(2))
    print(f'columns: {df.dtypes}')
    print(f'rows: f year == 2019: {len(df)}')
    return df 

@task()
def write_local(df: pd.DataFrame, year: int, dataset_file: str) -> Path:
    """Write DataFrame out locally as parquet file"""
    path = Path(f'data/{year}/{dataset_file}.parquet')
    df.to_parquet(path, compression='gzip')
    return path

@task()
def write_gcs(path: Path) -> None:
    """Upload local parquet file to GCS"""
    gcs_block = GcsBucket.load("de-week-two-example")
    gcs_block.upload_from_path(from_path = f'{path}', to_path = path)
    return
    
@flow()
def etl_web_to_gcs(year: int, month: int) -> None:
    """The main ETL function"""
    dataset_file = f'fhv_tripdata_{year}-{month:02}'
    dataset_url = f'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/fhv/{dataset_file}.csv.gz'
    #  https://github.com/DataTalksClub/nyc-tlc-data/releases/download/fhv/fhv_tripdata_2019-01.csv.gz
    # https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2019-01.csv.gz

    df = fetch(dataset_url)
    df_clean = clean(df)
    path = write_local(df_clean, year, dataset_file)
    write_gcs(path)
    # print(f"GCS: ./data/{year}/{dataset_file}")

@flow()
def etl_parent_flow(
    months: list[int] = [11], year: int = 2020
):
    for month in months:
        etl_web_to_gcs(year, month)

if __name__ == '__main__':
    months = [11]
    year = 2020
    etl_parent_flow(months, year)
