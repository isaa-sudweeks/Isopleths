"""Scientific edge cases for hourly matching and VOC completeness."""
import unittest

import pandas as pd

from data_processing.colorado_hourly import SR_FACTOR, build_table


class HourlyTableTests(unittest.TestCase):
    def setUp(self):
        self.selection = {
            "site": "08-059-0006", "years": [2024],
            "voc_parameters": {"43102": "Total NMOC", "43202": "Ethane",
                               "43502": "Formaldehyde", "43503": "Acetaldehyde"},
            "supplemental_organic_parameters": {"43141": "n-Dodecane", "43245": "1-Hexene"},
        }
        # Summer timestamps exercise the difference between fixed MST and DST.
        self.dt = pd.Timestamp("2024-07-01 12:00")
        rows = []
        for code, value, units, duration in [
            ("43202", 2., "Parts per billion Carbon", "1 HOUR"),
            ("43141", 0., "Parts per billion Carbon", "1 HOUR"),
            ("43245", 3., "Parts per billion Carbon", "1 HOUR"),
            ("43102", 500., "Parts per billion Carbon", "1 HOUR"),
            ("43502", 100., "Parts per billion Carbon", "8 HOUR"),
            ("42601", -.1, "Parts per billion", "1 HOUR"),
            ("42602", 1.1, "Parts per billion", "1 HOUR"),
            ("44201", .05, "Parts per million", "1 HOUR"),
            ("63301", 1., "Langleys/minute", "1 HOUR"),
        ]:
            rows.append({"dt": self.dt, "dt_utc": self.dt.tz_localize("UTC") + pd.Timedelta(hours=7),
                         "parameter_code": code, "value": value, "units_of_measure": units,
                         "sample_duration": duration, "qualifier": "", "review": False})
        self.raw = pd.DataFrame(rows)

    def table(self, raw=None):
        return build_table(self.raw if raw is None else raw, self.selection)[0]

    def test_no_double_counting_correct_units_and_fixed_standard_time(self):
        table = self.table()
        row = table.loc[self.dt]
        self.assertEqual(row.VOC, 5.)  # Neither NMOC nor 8-hour carbonyls enter.
        self.assertEqual(row.voc_species_present, 3)  # Numeric zero is observed.
        self.assertAlmostEqual(row.NOx, 1.)
        self.assertEqual(row.Ozone, 50.)
        self.assertAlmostEqual(row.solar_radiation_w_m2, SR_FACTOR)
        self.assertEqual(row.dt_utc.hour, 19)  # Not 18:00 (daylight time).
        self.assertTrue(row.negative_NO)  # Preserve, rather than clip, -.1.
        self.assertTrue(row.all_inputs_available)
        self.assertEqual(len(table), 8784)  # Leap-year calendar, including gaps.

    def test_missing_species_never_becomes_zero_or_complete_total(self):
        table = self.table(self.raw.loc[self.raw.parameter_code.ne("43245")])
        row = table.loc[self.dt]
        self.assertTrue(pd.isna(row.VOC))
        self.assertEqual(row.VOC_partial_ppbc, 2.)
        self.assertFalse(row.all_inputs_available)
        self.assertTrue(pd.isna(table.iloc[0].VOC_partial_ppbc))

    def test_missing_no2_is_not_replaced_by_noy(self):
        raw = self.raw.copy()
        raw.loc[raw.parameter_code.eq("42602"), "parameter_code"] = "42600"
        self.assertTrue(pd.isna(self.table(raw).loc[self.dt, "NOx"]))

    def test_ambiguous_monitor_duplicates_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate hourly"):
            self.table(pd.concat([self.raw, self.raw.iloc[[0]]]))

    def test_unexpected_units_fail(self):
        raw = self.raw.copy()
        raw.loc[raw.parameter_code.eq("44201"), "units_of_measure"] = "Parts per billion"
        with self.assertRaisesRegex(ValueError, "Unexpected units"):
            self.table(raw)

    def test_quality_review_does_not_silently_delete_numeric_values(self):
        raw = self.raw.copy()
        raw.loc[raw.parameter_code.eq("43202"), ["qualifier", "review"]] = ["LK - Possible bias", True]
        row = self.table(raw).loc[self.dt]
        self.assertEqual(row.VOC, 5.)
        self.assertTrue(row.all_inputs_available)
        self.assertFalse(row.all_inputs_no_review)


if __name__ == "__main__":
    unittest.main()
