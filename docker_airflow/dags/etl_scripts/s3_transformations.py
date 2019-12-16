#!/usr/bin/python
# the code above ensures this script is treated as an executable python script

import boto3
import json
import pandas as pd 
from datetime import datetime
import csv
from dateutil.parser import parse
# TODO figure out if this is the correct path when we run from dags folder
from etl_scripts.s3_data_class import web_tracked_data
import logging

# TODO change this to "etl_scripts/" later and figure out where to insert it below
etl_scripts_path = ""
cron_logs_csv_name = "cron_logs.csv"

current_time_for_log_file = datetime.utcnow()
# set logger 
logging.basicConfig(format = '%(asctime)-25s %(levelname)-7s %(module)-10s %(lineno)-5s %(funcName)-28s %(message)-8s',
                    filename = f'logging_logs/{current_time_for_log_file}.log',
                    level=logging.DEBUG)

def get_last_time_check_s3_object_resources():
    column_name_time_checked_s3 = 'time_checked_s3'
    df_crons = pd.read_csv(f'{cron_logs_csv_name}', names=[column_name_time_checked_s3])
    last_row_index = len(df_crons)-1
    logging.info(f"last row in {cron_logs_csv_name} {last_row_index}")
    last_checked_s3_time_str = df_crons.at[last_row_index, column_name_time_checked_s3]
    last_checked_s3_time_datetime = parse(last_checked_s3_time_str)
    logging.info(f"last_checked_s3_time_datetime in {cron_logs_csv_name} {last_checked_s3_time_datetime}")
    return last_checked_s3_time_datetime

def write_s3_time_checked_to_csv(current_time):
    with open('{cron_logs_csv_name}', 'a') as csv_file:
        writer_object = csv.writer(csv_file)
        writer_object.writerow([current_time])
    return None

def verify_if_we_need_to_do_tl(last_checked_s3_datetime, last_modified_s3_object_date):
    logging.info(f"last_checked_s3_time_datetime: {last_checked_s3_datetime}")
    logging.info(f"last_modified_s3_object_date: {last_modified_s3_object_date}")
    if last_modified_s3_object_date > last_checked_s3_datetime:
        tl_needed_status = True
    else:
        tl_needed_status = False
    return tl_needed_status

def transform_s3_data_into_list_of_dict_events(s3_object_resource):
    # get() retrieves objects from S3; https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Object.get
    # Body key has a value of streaming object as a dict;  apply read method to output bytes object; https://botocore.amazonaws.com/v1/documentation/api/latest/reference/response.html
    response = s3_object_resource.get()['Body'].read()
    # decoding is like reading data into memory; converts bytes to string
    response_str = response.decode('utf-8')
    # adds comma delimiter between pseudo JSON blobs in string
    response_str_delimited = "[{}]".format(response_str.replace("}{","},{"))
    # converts string of pseudo JSON blobs into Python dictionary
    list_of_dict_events = json.loads(response_str_delimited)
    return list_of_dict_events

def create_master_dataframe(list_dict_events):
    df = pd.DataFrame(list_dict_events)
    return df

def append_additional_events_to_master_dataframe(df, list_of_dict_events):
    logging.info(f"list_of_dict_events: {list_of_dict_events}")
    df_new_object = pd.DataFrame(list_of_dict_events)
    logging.info(f"df_new_object: {df_new_object}")
    df = df.append(df_new_object, ignore_index=True, sort=False)
    return df

def verify_if_new_s3_objects_exist(s3_objects_collection, s3_resource, bucket_name, last_checked_s3_datetime):
    last_modified_s3_object = list(s3_objects_collection)[-1]
    # key is name of object as string with date prefix of "YYYY/MM/DD/HH"
    last_modified_s3_object_key_name = last_modified_s3_object.key
    # object identified by a bucket name and key name (https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#object)
    last_modified_s3_object_resource = s3_resource.Object(bucket_name, last_modified_s3_object_key_name)
    last_modified_s3_object_date = last_modified_s3_object_resource.last_modified
    logging.info(f"last_modified_s3_object_date NO TZ {last_modified_s3_object_date}")
    # removes +00:00 at end of datetime
    last_modified_s3_object_date = last_modified_s3_object_resource.last_modified.replace(tzinfo=None)
    logging.info(f"last_modified_s3_object_date tzinfo=None {last_modified_s3_object_date}")
    tl_needed_status = verify_if_we_need_to_do_tl(last_checked_s3_datetime=last_checked_s3_datetime, last_modified_s3_object_date=last_modified_s3_object_date)
    
    return tl_needed_status

def load_all_s3_objects_into_dataframe(s3_objects_collection, s3_resource, bucket_name, last_checked_s3_datetime):
    # assign variable df to the value of None
    df = None
    # the s3_objects_collection includes ALL OBJECTS with the prefix='web-data/raw/'  
    for s3_object_resource in s3_objects_collection:
    # key is name of object as string with date prefix of "YYYY/MM/DD/HH"...
        logging.info(f"s3_object_resource: {s3_object_resource}")
        key_name = s3_object_resource.key
        s3_object_resource = s3_resource.Object(bucket_name, key_name)

        last_modified_s3_object_date = s3_object_resource.last_modified
        last_modified_s3_object_date = last_modified_s3_object_date.replace(tzinfo=None)

        # we're checking if *each* s3 object was last modified more recently than our last cron job
        tl_needed_status = verify_if_we_need_to_do_tl(last_checked_s3_datetime, last_modified_s3_object_date)
        if tl_needed_status is True:
            list_of_dict_events = transform_s3_data_into_list_of_dict_events(s3_object_resource=s3_object_resource)
            logging.info(f"list_of_dict_events: {list_of_dict_events}")
            if df is None:
                df = create_master_dataframe(list_dict_events=list_of_dict_events)
                logging.info(f"df: {df}")
            else:
                logging.info("this condition handles if we have multiple s3 objects added from a single cron job")
                logging.info("df has been created with new objects that must undergo transform and load process...")
                df = append_additional_events_to_master_dataframe(df=df, list_of_dict_events=list_of_dict_events)
    return df

def horsing_around_web_data_transformations():
    horsing_around_bucket_name = 'horsing-around-bucket'
    s3_resource = boto3.resource('s3')
    horsing_around_bucket_object = s3_resource.Bucket(horsing_around_bucket_name)
    # ensures we only examine objects with the prefix of "web-data/raw"
    s3_horsing_around_web_data_raw_objects_collection = horsing_around_bucket_object.objects.filter(Prefix='web-data/raw/')    
    # current_time is nearly when checked S3. write this to our cron logs CSV once all transformations complete
    current_time = datetime.utcnow()
    last_timestamp_dag_run_to_check_s3 = get_last_time_check_s3_object_resources()
    tl_needed_status = verify_if_new_s3_objects_exist(s3_objects_collection=s3_horsing_around_web_data_raw_objects_collection, 
                                                      s3_resource=s3_resource, 
                                                      bucket_name=horsing_around_bucket_name, 
                                                      last_checked_s3_datetime=last_timestamp_dag_run_to_check_s3
                                                      )
    if tl_needed_status is True:
        # there's an object in S3 with a last modified date more recent than our most recent cron job
        # we only call load_all_s3_objects_into_dataframe if we know there's new s3 objects
        df = load_all_s3_objects_into_dataframe(s3_objects_collection=s3_horsing_around_web_data_raw_objects_collection,
                                                s3_resource=s3_resource,
                                                bucket_name=horsing_around_bucket_name,
                                                last_checked_s3_datetime=last_timestamp_dag_run_to_check_s3
                                                )
        
        # VERIFY WE HAVE DATA COLLECTED FOR EVENT-SPECIFIC TABLES BEFORE CREATING TABLES AND UPLOADING TO S3
        column_names = df.columns
        event_status = False
        event_column_name = 'event'
        # type column name always exists
        unique_type_values = df['type'].unique().tolist()
        # event name column doesn't always exist
        if event_column_name in column_names:
            unique_event_names = df[event_column_name].unique().tolist()
            event_status = True
            
        # USERS --------------------------------------------------------------------------------
        segment_event_type_identify = 'identify'
        if segment_event_type_identify in unique_type_values:
            users = web_tracked_data(df=df,
                                        segment_event_type=segment_event_type_identify, 
                                        relevant_event_attributes=['traits', 'userId', 'timestamp'],
                                        unpack_column='traits',
                                        map_column_names_dict={'userId': 'user_id'},
                                        event_description='users',
                                        bucket_object=horsing_around_bucket_object,
                                        checked_s3_time=current_time
                                    )  

            df_users = users.filter_s3_objects_in_df_for_one_segment_event_type()
            users.transform_and_load_data_into_s3(dataframe_one_event_name=df_users)
        
        if event_status is True:
            # POSTS --------------------------------------------------------------------------------
            segment_event_name_posts_created = 'Post Created'
            if segment_event_name_posts_created in unique_event_names:
                posts_created = web_tracked_data(df=df, 
                                                segment_event_type='event', 
                                                segment_event_name = segment_event_name_posts_created,
                                                relevant_event_attributes=['properties'],
                                                unpack_column='properties',
                                                map_column_names_dict={'author': 'user_id', 'created_at': 'published_at'},
                                                event_description='posts',
                                                bucket_object=horsing_around_bucket_object,
                                                checked_s3_time=current_time
                                                )
                df_posts = posts_created.filter_s3_objects_in_df_for_one_segment_event_type(segment_event_name=posts_created.segment_event_name)
                posts_created.transform_and_load_data_into_s3(dataframe_one_event_name=df_posts)

            # FOLLOWS --------------------------------------------------------------------------------
            segment_event_name_follows = 'Follow User'
            if segment_event_name_follows in unique_event_names:
                follows = web_tracked_data(df=df, 
                                           segment_event_type='event', 
                                           segment_event_name = segment_event_name_follows,
                                           relevant_event_attributes=['event', 'properties', 'userId', 'timestamp'],
                                           unpack_column='properties',
                                           map_column_names_dict={'userId': 'user_id', 'user_id': 'user_id_recipient'},
                                           event_description='follows',
                                           bucket_object=horsing_around_bucket_object,
                                           checked_s3_time=current_time
                                          )
                df_follows = follows.filter_s3_objects_in_df_for_one_segment_event_type(segment_event_name=follows.segment_event_name)
                follows.transform_and_load_data_into_s3(dataframe_one_event_name=df_follows)
        
            # UNFOLLOWS --------------------------------------------------------------------------------
            segment_event_name_unfollows = 'Unfollow User'
            if segment_event_name_unfollows in unique_event_names:
                unfollows = web_tracked_data(df=df, 
                                             segment_event_type='event', 
                                             segment_event_name = segment_event_name_unfollows,
                                             relevant_event_attributes=['event', 'properties', 'userId', 'timestamp'],
                                             unpack_column='properties',
                                             map_column_names_dict={'userId': 'user_id', 'user_id': 'user_id_recipient'},
                                             event_description='unfollows',
                                             bucket_object=horsing_around_bucket_object,
                                             checked_s3_time=current_time
                                             )
                df_unfollows = unfollows.filter_s3_objects_in_df_for_one_segment_event_type(segment_event_name=unfollows.segment_event_name)
                unfollows.transform_and_load_data_into_s3(dataframe_one_event_name=df_unfollows)

    # log time to cron_logs.csv only after all etl transformations are successful
    # TODO figure out how to successfully log when a cron job is completed with the transformations
    write_s3_time_checked_to_csv(current_time=current_time)

if __name__ == "__main__":
    horsing_around_web_data_transformations()