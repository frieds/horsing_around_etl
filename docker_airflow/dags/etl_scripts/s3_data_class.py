import boto3
import pandas as pd 
from datetime import datetime

etl_scripts_path = "etl_scripts/"

class web_tracked_data(object):
    PARQUET = 'parquet' 
    TRANSFORMED_S3_PREFIX_LOCATION = "web-data/transformed"

    def __init__(self, df, segment_event_type, relevant_event_attributes, unpack_column, 
                       map_column_names_dict, event_description, bucket_object, 
                       checked_s3_time, segment_event_name=None):
        # segment_event_type can be tracking event or identify event
        self.segment_event_type = segment_event_type
        self.relevant_event_attributes = relevant_event_attributes
        self.df = df
        self.unpack_column = unpack_column
        self.map_column_names_dict = map_column_names_dict
        self.event_description = event_description
        self.bucket_object = bucket_object
        self.checked_s3_time = checked_s3_time
        self.segment_event_name = segment_event_name
    
    def filter_s3_objects_in_df_for_one_segment_event_type(self, segment_event_name=None):
        if self.segment_event_type == 'event' and segment_event_name is not None:
            df = self.df[self.df['event']==segment_event_name][self.relevant_event_attributes]
        elif self.segment_event_type == 'identify' and segment_event_name is None:
            df = self.df[self.df['type']=='identify'][self.relevant_event_attributes]
        else:
            pass
        return df

    def unpack_dictionaries_in_dataframe(self, df):
        df = df.drop(self.unpack_column, 1).assign(**df[self.unpack_column].apply(pd.Series))
        return df

    def rename_unpacked_column_names_in_df(self, df, column_mapper):   
        df = df.rename(columns=column_mapper)
        return df

    def create_file_path_for_parquet_file(self):
        file_path_for_parquet_file = f"{etl_scripts_path}recent_converted_parquet_files/df_{self.event_description}.{self.PARQUET}"
        return file_path_for_parquet_file

    def compress_dataframe_and_write_to_disk(self, df, file_path):
        df.to_parquet(fname=file_path, index=False)
        return None

    def create_new_key_name_for_uploading_s3_object(self):
        short_date = self.checked_s3_time.strftime("%Y/%m/%d/%H")
        long_date = self.checked_s3_time.strftime("%Y-%m-%d-%H-%M-%S")
        transformed_key_name = f"{self.TRANSFORMED_S3_PREFIX_LOCATION}/{self.event_description}/{short_date}/horsing_around_kinesis_firehose-{long_date}"
        return transformed_key_name

    def upload_file_to_s3_bucket(self, file_path):
        transformed_key_name = self.create_new_key_name_for_uploading_s3_object()
        self.bucket_object.upload_file(Filename=file_path, Key=transformed_key_name)
        return None

    def transform_and_load_data_into_s3(self, dataframe_one_event_name):
        df = self.unpack_dictionaries_in_dataframe(df=dataframe_one_event_name)
        df = self.rename_unpacked_column_names_in_df(df=df, column_mapper=self.map_column_names_dict)
        file_path = self.create_file_path_for_parquet_file()
        self.compress_dataframe_and_write_to_disk(df=df, file_path=file_path)
        self.upload_file_to_s3_bucket(file_path=file_path)
        return None