import unittest
from dataengineeringutils.pd_metadata_conformance import _pd_df_cols_match_metadata_cols
from dataengineeringutils.pd_metadata_conformance import _pd_df_cols_match_metadata_cols_ordered
from dataengineeringutils.pd_metadata_conformance import _check_pd_df_cols_match_metadata_cols
from dataengineeringutils.pd_metadata_conformance import _check_pd_df_cols_match_metadata_cols_ordered
from dataengineeringutils.pd_metadata_conformance import _check_pd_df_datatypes_match_metadata_data_types
from dataengineeringutils.pd_metadata_conformance import _remove_paritions_from_table_metadata
from dataengineeringutils.pd_metadata_conformance import *
import pandas as pd
import os
import json
import random

def read_json_from_path(path):
    with open(path) as f:
        return_json = json.load(f)
    return return_json

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

def td_path(path):
    return os.path.join(THIS_DIR, "test_data", path)

class ConformanceTest(unittest.TestCase) :
    """
    Test packages utilities functions
    """
    def test_pd_df_contains_same_columns_as_metadata(self) :

        df = pd.read_csv(td_path("test_csv_data_valid.csv"))
        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))

        self.assertTrue(_pd_df_cols_match_metadata_cols(df, table_metadata))
        _check_pd_df_cols_match_metadata_cols(df, table_metadata)

        df = pd.read_csv(td_path("test_csv_data_additional_col.csv"))
        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))

        self.assertFalse(_pd_df_cols_match_metadata_cols(df, table_metadata))
        with self.assertRaises(ValueError):
            _check_pd_df_cols_match_metadata_cols(df, table_metadata)


    def test_pd_df_cols_matches_metadata_column_ordered(self) :

        df = pd.read_csv(td_path("test_csv_data_valid.csv"))
        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))

        self.assertTrue(_pd_df_cols_match_metadata_cols_ordered(df, table_metadata))
        _check_pd_df_cols_match_metadata_cols_ordered(df, table_metadata)

        df = pd.read_csv(td_path("test_csv_data_additional_col.csv"))
        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))

        self.assertFalse(_pd_df_cols_match_metadata_cols_ordered(df, table_metadata))
        with self.assertRaises(ValueError):
            _check_pd_df_cols_match_metadata_cols_ordered(df, table_metadata)

    def test_pd_df_conforms_to_metadata_data_types(self):

        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))
        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)
        self.assertTrue(pd_df_datatypes_match_metadata_data_types(df, table_metadata))

        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))
        df = pd.read_csv(td_path("test_csv_data_valid.csv"))
        self.assertFalse(pd_df_datatypes_match_metadata_data_types(df, table_metadata))

    def test_impose_metadata_column_order_on_pd_df(self):

        # Test tables with right number of cols, possibly in wrong order

        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))
        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)

        # This should be a no-op
        df = impose_metadata_column_order_on_pd_df(df, table_metadata)
        _check_pd_df_cols_match_metadata_cols_ordered(df, table_metadata)

        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid_wrong_order.csv"), table_metadata)

        with self.assertRaises(ValueError):
            _check_pd_df_cols_match_metadata_cols_ordered(df, table_metadata)

        df = impose_metadata_column_order_on_pd_df(df, table_metadata)
        self.assertTrue(_pd_df_cols_match_metadata_cols_ordered(df, table_metadata))

        # Test tables with missing col
        df = pd_read_csv_using_metadata(td_path("test_csv_data_missing_col.csv"), table_metadata)

        with self.assertRaises(ValueError):  # Shouldn't add cols unless explicitly specified
            impose_metadata_column_order_on_pd_df(df, table_metadata)

        df = impose_metadata_column_order_on_pd_df(df, table_metadata, create_cols_if_not_exist=True)
        self.assertTrue(_pd_df_cols_match_metadata_cols_ordered(df, table_metadata))

        # Test tables with superflouous column
        df = pd_read_csv_using_metadata(td_path("test_csv_data_additional_col.csv"), table_metadata)

        with self.assertRaises(ValueError):  # Shouldn't remove cols unless explicitly specified
            impose_metadata_column_order_on_pd_df(df, table_metadata,delete_superflous_colums=False)

        df = impose_metadata_column_order_on_pd_df(df, table_metadata)

        self.assertTrue(_pd_df_cols_match_metadata_cols_ordered(df, table_metadata))

        # Superflous and missing columns in random order
        df = pd_read_csv_using_metadata(td_path("test_csv_data_additional_col.csv"), table_metadata)

        cols = list(df.columns)
        random.shuffle(cols)
        df = df[cols]
        del df["myint"]

        df = impose_metadata_column_order_on_pd_df(df, table_metadata, create_cols_if_not_exist=True)
        self.assertTrue(_pd_df_cols_match_metadata_cols_ordered(df, table_metadata))

    def test_impose_metadata_data_types_on_pd_df(self):
        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))
        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)
        df = impose_metadata_data_types_on_pd_df(df, table_metadata)

        self.assertTrue(pd_df_datatypes_match_metadata_data_types(df, table_metadata))

        df = pd.read_csv(td_path("test_csv_data_valid.csv"))

        df = impose_metadata_data_types_on_pd_df(df, table_metadata)

        self.assertTrue(pd_df_datatypes_match_metadata_data_types(df, table_metadata))

        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)
        df.loc[0, "myint"] = "hello"
        with self.assertRaises(ValueError):
            df = impose_exact_conformance_on_pd_df(df, table_metadata)

        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)
        df.loc[0, "myint"] = "hello"

        df = impose_metadata_data_types_on_pd_df(df, table_metadata, errors='ignore')

        # Check that floats get converted to ints
        df = pd.read_csv(td_path("test_csv_data_valid.csv"))
        df.loc[0, "myint"] = 1.0
        df.loc[1, "myint"] = 1324.0
        df.loc[2, "myint"] = 41.0
        df = impose_metadata_data_types_on_pd_df(df, table_metadata)
        check_pd_df_exactly_conforms_to_metadata(df, table_metadata)
        self.assertTrue(type(df.loc[0, "myint"]) == np.typeDict["int64"])

        # Check that a mixed column correctly converts to a string
        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)
        df.loc[2,"mychar"] = 1.23

        self.assertTrue(type(df.loc[2,"mychar"]) == float)
        df = impose_metadata_data_types_on_pd_df(df, table_metadata)
        self.assertTrue(type(df.loc[2,"mychar"]) == str)


    def test_impose_exact_conformance_on_pd_df(self):
        table_metadata = read_json_from_path(td_path("test_table_metadata_valid.json"))
        df = pd_read_csv_using_metadata(td_path("test_csv_data_additional_col.csv"), table_metadata)
        df = impose_exact_conformance_on_pd_df(df, table_metadata)
        check_pd_df_exactly_conforms_to_metadata(df, table_metadata)

        df = pd_read_csv_using_metadata(td_path("test_csv_data_additional_col.csv"), table_metadata)
        df = impose_exact_conformance_on_pd_df(df, table_metadata)
        check_pd_df_exactly_conforms_to_metadata(df, table_metadata)

        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid_wrong_order.csv"), table_metadata)
        df = impose_exact_conformance_on_pd_df(df, table_metadata)
        check_pd_df_exactly_conforms_to_metadata(df, table_metadata)

        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)
        df.loc[0, "myint"] = "hello"
        with self.assertRaises(ValueError):
            df = impose_exact_conformance_on_pd_df(df, table_metadata)

        df = pd_read_csv_using_metadata(td_path("test_csv_data_missing_col.csv"), table_metadata)
        with self.assertRaises(ValueError):
            df = impose_exact_conformance_on_pd_df(df, table_metadata)

        df = pd_read_csv_using_metadata(td_path("test_csv_data_valid.csv"), table_metadata)

        cols = list(df.columns)
        random.shuffle(cols)
        df = df[cols]

        df = impose_exact_conformance_on_pd_df(df, table_metadata)
        _check_pd_df_cols_match_metadata_cols_ordered(df, table_metadata)
        df = pd_read_csv_using_metadata(td_path("test_csv_data_additional_col.csv"), table_metadata)
        del df["myint"]

        with self.assertRaises(ValueError):
            df = impose_exact_conformance_on_pd_df(df, table_metadata)


    def test_impose_exact_conformance_on_pd_df(self):
        table_metadata_partitions = read_json_from_path(td_path("test_table_metadata_partition.json"))
        table_metadata_no_partitions = read_json_from_path(td_path("test_table_metadata_valid.json"))
        table_metadata_partitions_removed = _remove_paritions_from_table_metadata(table_metadata_partitions)
        self.assertTrue(table_metadata_no_partitions == table_metadata_partitions_removed)

    def test_mixtype_column_behaves(self):
        table_metadata = read_json_from_path(td_path("test_table_metadata_mixedtype_col.json"))
        df = pd_read_csv_using_metadata(td_path("test_csv_data_mixedtype_col.csv"), table_metadata)

        self.assertTrue(list(df["mixedtype"]) == ["hello", "1.2", "1"])
        self.assertTrue(list(df["mychar"]) == ["a", "hello","hello"])

        df = pd.read_csv(td_path("test_csv_data_mixedtype_col.csv"))

        df = impose_metadata_data_types_on_pd_df(df, table_metadata)
        self.assertTrue(list(df["mixedtype"]) == ["hello", "1.2", "1"])
        self.assertTrue(list(df["mychar"]) == ["a", "hello","hello"])

        df = pd.read_csv(td_path("test_csv_data_mixedtype_col.csv"))
        df.loc[1, "mixedtype"] = 1.3
        df = impose_metadata_data_types_on_pd_df(df, table_metadata)
        self.assertTrue(list(df["mixedtype"]) == ["hello", "1.3", "1"])




