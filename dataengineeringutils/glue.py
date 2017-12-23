import pandas as pd
import numpy as np
import boto3
import json
import pkg_resources
import dataengineeringutils.meta as meta_utils
from dataengineeringutils.datatypes import translate_metadata_type_to_glue_type
from dataengineeringutils.utils import dict_merge
from dataengineeringutils.basic import read_json

from io import StringIO
glue_client = boto3.client('glue', 'eu-west-1')
s3_resource = boto3.resource('s3')

# Creates glue table spec from meta data
def get_glue_table_spec_from_meta(meta_object, template_type = 'csv') :
    table_spec = get_table_definition_template(table_name = meta_object['table_name'],
        table_desc = meta_object['table_description'],
        table_col_meta = meta_object['columns'],
        location = 's3://' + meta_object['bucket'] + '/' + meta_object['table_name'],
        template_type = template_type)

    return table_spec


def get_table_col_meta_template(column_names, overrides = None) :
    if overrides is None :
        overrides = []

    base_types = meta_utils.get_base_data_types()

    keys = list(overrides)

    # Error checking
    for k in keys :
        if overrides[k] not in base_types :
            raise ValueError("Column name: \"{}\" in input overrides: has an invalid datatype. Valid datatypes are {}".format(k,", ".join(base_types)))

    # Create meta data
    col_meta = []
    for c in column_names :
        col_meta.append({'Name' : c,
                         'Type' : 'string' if c not in keys else overrides[c]})
    return(col_meta)


# Save a dataframe to an S3 bucket (removes headers)
def df_to_csv_s3(df, bucket, path):
    csv_buffer = StringIO()

    #Skip headers is necessary for now - see here: https://twitter.com/esh/status/811396849756041217
    df.to_csv(csv_buffer, index=False, header=False)

    s3_f = s3_resource.Object(bucket, path)
    response = s3_f.put(Body=csv_buffer.getvalue())


def get_table_definition_template(template_type = 'csv', **kwargs):
    """Get a definition template that can be used with Glue for the various template types

    Args:
        template_type: Allowed values are {'csv', 'parquet', 'avro', 'orc'}
        **kwargs: Arbitrary keyword arguments which will be added to the template
    """
    base_io = pkg_resources.resource_stream(__name__, "specs/base.json")
    base = json.load(base_io)

    conversion = {
        "avro": pkg_resources.resource_stream(__name__, "specs/avro_specific.json"),
        "csv": pkg_resources.resource_stream(__name__, "specs/csv_specific.json"),
        "orc": pkg_resources.resource_stream(__name__, "specs/orc_specific.json"),
        "par": pkg_resources.resource_stream(__name__, "specs/par_specific.json"),
        "parquet": pkg_resources.resource_stream(__name__, "specs/par_specific.json")
        }

    specific_io = conversion[template_type]
    specific = json.load(specific_io)
    dict_merge(base, specific)
    dict_merge(base, kwargs)
    return base


def create_database(db_name, db_description) :
    db = {
        "DatabaseInput": {
            "Description": db_description,
            "Name": db_name,
        }
    }
    try :
        glue_client.delete_database(Name=db_name)
    except :
        pass

    response = glue_client.create_database(**db)

# Add table to database in glue
def create_table_from_def(db_name, table_name, table_spec) :
    try :
        glue_client.delete_table(
            DatabaseName=db_name,
            Name=table_name
        )
    except :
        pass

    response = glue_client.create_table(
        DatabaseName=db_name,
        TableInput=table_spec)

# Does what it says on the tin
def take_script_and_run_job(input_script_path, output_script_path, role, job_name, script_bucket = "alpha-dag-data-engineers-raw", temp_dir = "s3://alpha-dag-data-engineers-raw/athena_out"):

    s3_f = s3_resource.Object(script_bucket, output_script_path)
    response= s3_f.put(Body=open(input_script_path, "rb"))

    job = {'AllocatedCapacity': 2,
     'Command': {
      'Name': 'glueetl',
      'ScriptLocation': 's3://{}/{}'.format(script_bucket, output_script_path)
     },
     'DefaultArguments': {'--TempDir': temp_dir,
      '--job-bookmark-option': 'job-bookmark-disable'},
     'ExecutionProperty': {'MaxConcurrentRuns': 1},
     'MaxRetries': 0,
     'Name': job_name,
     'Role': role}

    response = glue_client.create_job(**job)
    response = glue_client.start_job_run(JobName=job_name)

def get_glue_column_spec_from_metadata(metadata):
    columns = metadata["metadata"]["columns"]
    glue_columns = []
    for c in columns:
        new_c = {}
        new_c["Name"] = c["name"]
        new_c["Comment"] = c["description"]
        new_c["Type"] = translate_metadata_type_to_glue_type(c["type"])
        glue_columns.append(new_c)
    return glue_columns