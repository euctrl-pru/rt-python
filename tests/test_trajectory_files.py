#!/usr/bin/env python
#
# Copyright (c) 2018 Via Technology Ltd. All Rights Reserved.
# Consult your license regarding permissions and restrictions.

import unittest
from numpy.testing import assert_almost_equal
from pru.trajectory_files import *


class TestTrajectoryFiles(unittest.TestCase):

    def test_create_original_cpr_filename(self):
        test_name = '1.201708011001tacop104ARCHIVED_OPLOG_ALL_CPR.gz'
        test_date = '2017-08-01'
        self.assertEqual(create_original_cpr_filename(test_date), test_name)

    def test_create_original_fr24_data_filenames(self):
        test_name_0 = 'FR24_ADSB_DATA_FLIGHTS_2017-08-01.csv.bz2'
        test_name_1 = 'FR24_ADSB_DATA_POINTS_2017-08-01.csv.bz2'
        test_date = '2017-08-01'
        filenames = create_original_fr24_data_filenames(test_date)
        self.assertEqual(len(filenames), 2)
        self.assertEqual(filenames[0], test_name_0)
        self.assertEqual(filenames[1], test_name_1)

    def test_create_flights_filename(self):
        test_name = 'fr24_flights_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_flights_filename(FR24, test_date), test_name)

    def test_create_events_filename(self):
        test_name = 'cpr_events_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_events_filename(CPR, test_date), test_name)

    def test_create_positions_filename(self):
        test_name = 'ref_positions_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_positions_filename(REF, test_date), test_name)

    def test_create_ref_positions_filename(self):
        test_name = 'fr24_ref_positions_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_ref_positions_filename(FR24, test_date), test_name)

    def test_create_raw_positions_filename(self):
        test_name = 'raw_fr24_positions_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_raw_positions_filename(FR24, test_date), test_name)

    def test_create_trajectories_filename(self):
        test_name = 'cpr_fr24_trajectories_2017-08-01.json'
        test_date = '2017-08-01'
        self.assertEqual(create_trajectories_filename(CPR_FR24, test_date), test_name)

    def test_create_error_metrics_filename(self):
        test_name = 'cpr_error_metrics_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_error_metrics_filename(CPR, test_date), test_name)

    def test_create_trajectory_metrics_filename(self):
        test_name = 'cpr_fr24_traj_metrics_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_trajectory_metrics_filename(CPR_FR24, test_date), test_name)

    def test_create_convert_cpr_filenames(self):
        test_date = '2017-08-01'
        names = create_convert_cpr_filenames(test_date)
        self.assertEqual(names[0], 'cpr_flights_2017-08-01.csv')
        self.assertEqual(names[1], 'cpr_events_2017-08-01.csv')
        self.assertEqual(names[2], 'raw_cpr_positions_2017-08-01.csv')

    def test_create_convert_fr24_filenames(self):
        test_date = '2017-08-01'
        names = create_convert_fr24_filenames(test_date)
        self.assertEqual(names[0], 'iata_fr24_flights_2017-08-01.csv')
        self.assertEqual(names[1], 'raw_fr24_positions_2017-08-01.csv')

    def test_create_fleet_data_filename(self):
        test_name = 'fleet_data_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_fleet_data_filename(test_date), test_name)

    def test_create_apds_flights_filename(self):
        test_name = 'apds_flights_2017-08-01_2017-08-31.csv'
        from_date = '2017-08-01'
        to_date = '2017-08-31'
        self.assertEqual(create_apds_flights_filename(from_date, to_date), test_name)

    def test_create_apds_events_filename(self):
        test_name = 'apds_events_2017-08-01_2017-08-31.csv'
        from_date = '2017-08-01'
        to_date = '2017-08-31'
        self.assertEqual(create_apds_events_filename(from_date, to_date), test_name)

    def test_create_apds_positions_filename(self):
        test_name = 'apds_positions_2017-08-01_2017-08-31.csv'
        from_date = '2017-08-01'
        to_date = '2017-08-31'
        self.assertEqual(create_apds_positions_filename(from_date, to_date), test_name)

    def test_create_convert_apds_filenames(self):
        from_date = '2017-08-01'
        to_date = '2017-08-31'
        names = create_convert_apds_filenames(from_date, to_date)
        self.assertEqual(names[0], 'apds_flights_2017-08-01_2017-08-31.csv')
        self.assertEqual(names[1], 'apds_positions_2017-08-01_2017-08-31.csv')
        self.assertEqual(names[2], 'apds_events_2017-08-01_2017-08-31.csv')

    def test_create_clean_position_data_filenames(self):
        test_process = CPR_FR24
        test_date = '2017-08-01'
        names = create_clean_position_data_filenames(test_process, test_date)
        self.assertEqual(names[0], 'cpr_fr24_positions_2017-08-01.csv')
        self.assertEqual(names[1], 'cpr_fr24_error_metrics_2017-08-01.csv')

    def test_create_analyse_position_data_filenames(self):
        test_process = CPR_FR24
        test_date = '2017-08-01'
        distance_tolerance = 0.5
        method = 'lm'
        names = create_analyse_position_data_filenames(test_process, test_date,
                                                       distance_tolerance, method)
        self.assertEqual(names[0], 'lm_05_cpr_fr24_trajectories_2017-08-01.json')
        self.assertEqual(names[1], 'lm_05_cpr_fr24_traj_metrics_2017-08-01.csv')

    def test_create_match_cpr_adsb_input_filenames(self):
        test_date = '2017-08-01'
        names = create_match_cpr_adsb_input_filenames(test_date)
        self.assertEqual(names[0], 'cpr_flights_2017-08-01.csv')
        self.assertEqual(names[1], 'fr24_flights_2017-08-01.csv')
        self.assertEqual(names[2], 'cpr_positions_2017-08-01.csv')
        self.assertEqual(names[3], 'fr24_positions_2017-08-01.csv')

    def test_create_matching_ids_filename(self):
        test_name = 'cpr_matching_ids_2017-08-01.csv'
        test_date = '2017-08-01'
        self.assertEqual(create_matching_ids_filename(CPR, test_date), test_name)

    def test_create_match_cpr_adsb_output_filenames(self):
        test_date = '2017-08-01'
        names = create_match_cpr_adsb_output_filenames(test_date)
        self.assertEqual(names[0], 'cpr_matching_ids_2017-08-01.csv')
        self.assertEqual(names[1], 'fr24_matching_ids_2017-08-01.csv')

    def test_create_merge_cpr_adsb_input_filenames(self):
        test_date = '2017-08-01'
        names = create_merge_cpr_adsb_input_filenames(test_date)
        self.assertEqual(names[0], 'cpr_matching_ids_2017-08-01.csv')
        self.assertEqual(names[1], 'fr24_matching_ids_2017-08-01.csv')
        self.assertEqual(names[2], 'cpr_flights_2017-08-01.csv')
        self.assertEqual(names[3], 'fr24_flights_2017-08-01.csv')
        self.assertEqual(names[4], 'cpr_positions_2017-08-01.csv')
        self.assertEqual(names[5], 'fr24_positions_2017-08-01.csv')
        self.assertEqual(names[6], 'cpr_events_2017-08-01.csv')

    def test_create_merge_cpr_adsb_output_filenames(self):
        test_date = '2017-08-01'
        names = create_merge_cpr_adsb_output_filenames(test_date)
        self.assertEqual(names[0], 'cpr_fr24_flights_2017-08-01.csv')
        self.assertEqual(names[1], 'raw_cpr_fr24_positions_2017-08-01.csv')
        self.assertEqual(names[2], 'cpr_fr24_events_2017-08-01.csv')

    def test_create_match_consecutive_day_input_filenames(self):
        test_date = '2017-08-01'
        names = create_match_consecutive_day_input_filenames(test_date)
        self.assertEqual(names[0], 'cpr_fr24_flights_2017-07-31.csv')
        self.assertEqual(names[1], 'cpr_fr24_flights_2017-08-01.csv')
        self.assertEqual(names[2], 'cpr_fr24_positions_2017-07-31.csv')
        self.assertEqual(names[3], 'cpr_fr24_positions_2017-08-01.csv')

    def test_create_merge_consecutive_day_input_filenames(self):
        test_date = '2017-08-01'
        names = create_merge_consecutive_day_input_filenames(test_date)
        self.assertEqual(names[0], 'prev_day_matching_ids_2017-08-01.csv')
        self.assertEqual(names[1], 'cpr_fr24_flights_2017-07-31.csv')
        self.assertEqual(names[2], 'cpr_fr24_flights_2017-08-01.csv')
        self.assertEqual(names[3], 'cpr_fr24_positions_2017-07-31.csv')
        self.assertEqual(names[4], 'cpr_fr24_positions_2017-08-01.csv')
        self.assertEqual(names[5], 'cpr_fr24_events_2017-07-31.csv')
        self.assertEqual(names[6], 'cpr_fr24_events_2017-08-01.csv')

    def test_create_merge_consecutive_day_output_filenames(self):
        test_date = '2017-08-01'
        names = create_merge_consecutive_day_output_filenames(test_date)
        self.assertEqual(names[0], 'new_cpr_fr24_flights_2017-07-31.csv')
        self.assertEqual(names[1], 'new_cpr_fr24_flights_2017-08-01.csv')
        self.assertEqual(names[2], 'new_cpr_fr24_positions_2017-07-31.csv')
        self.assertEqual(names[3], 'new_cpr_fr24_positions_2017-08-01.csv')
        self.assertEqual(names[4], 'new_cpr_fr24_events_2017-07-31.csv')
        self.assertEqual(names[5], 'new_cpr_fr24_events_2017-08-01.csv')

    def test_create_match_apds_input_filenames(self):
        test_date = '2017-08-02'
        names = create_match_apds_input_filenames('2017-08-01', '2017-08-31', test_date)
        self.assertEqual(names[0], 'cpr_fr24_flights_2017-08-02.csv')
        self.assertEqual(names[1], 'apds_flights_2017-08-01_2017-08-31.csv')
        self.assertEqual(names[2], 'cpr_fr24_events_2017-08-02.csv')
        self.assertEqual(names[3], 'apds_events_2017-08-01_2017-08-31.csv')

    def test_create_merge_apds_input_filenames(self):
        test_date = '2017-08-02'
        names = create_merge_apds_input_filenames('2017-08-01', '2017-08-31', test_date)
        self.assertEqual(names[0], 'apds_matching_ids_2017-08-02.csv')
        self.assertEqual(names[1], 'cpr_fr24_positions_2017-08-02.csv')
        self.assertEqual(names[2], 'apds_positions_2017-08-01_2017-08-31.csv')
        self.assertEqual(names[3], 'cpr_fr24_events_2017-08-02.csv')
        self.assertEqual(names[4], 'apds_events_2017-08-01_2017-08-31.csv')

    def test_create_merge_apds_output_filenames(self):
        test_date = '2017-08-02'
        names = create_merge_apds_output_filenames(test_date)
        self.assertEqual(names[0], 'apds_cpr_fr24_positions_2017-08-02.csv')
        self.assertEqual(names[1], 'apds_cpr_fr24_events_2017-08-02.csv')


if __name__ == '__main__':
    unittest.main()
