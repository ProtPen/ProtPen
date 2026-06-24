import unittest
from unittest.mock import patch
from protpen import merge_utils
from unittest.mock import patch, MagicMock, mock_open
from unittest import TestCase
from unittest.mock import patch, mock_open, MagicMock
import protpen.merge_utils as merge_utils


class TestMergeUtils(unittest.TestCase):
    def test_create_header_mapping(self):
        headers = ["query", "description", "score"]
        expected = {
            "query": "query",
            "description": "egg_description",
            "score": "egg_score",
        }
        result = merge_utils.create_header_mapping(headers, "egg")
        self.assertEqual(result, expected)

    def test_merge_data_basic(self):
        eggnog_data = {
            "Q1": {"query": "Q1", "description": "egg1", "score": "10"},
            "Q2": {"query": "Q2", "description": "egg2", "score": "20"},
        }
        foldseek_data = {
            "Q1": {"query": "Q1", "alignment": "fs1", "evalue": "1e-5"},
            "Q3": {"query": "Q3", "alignment": "fs3", "evalue": "0.0"},
        }
        eggnog_headers = ["query", "description", "score"]
        foldseek_headers = ["query", "alignment", "evalue"]

        headers, rows = merge_utils.merge_data(
            eggnog_data, eggnog_headers, foldseek_data, foldseek_headers
        )

        assert headers == [
            "query",
            "eggnog_description",
            "eggnog_score",
            "foldseek_alignment",
            "foldseek_evalue",
        ]
        # Full outer join: Q1 (matched), Q2 (EggNOG-only), Q3 (Foldseek-only)
        assert len(rows) == 3

        q1 = next(r for r in rows if r["query"] == "Q1")
        self.assertEqual(q1["eggnog_description"], "egg1")
        self.assertEqual(q1["foldseek_alignment"], "fs1")

        q2 = next(r for r in rows if r["query"] == "Q2")
        self.assertEqual(q2["eggnog_description"], "egg2")
        self.assertEqual(q2["foldseek_alignment"], "")

        q3 = next(r for r in rows if r["query"] == "Q3")
        self.assertEqual(q3["eggnog_description"], "")
        self.assertEqual(q3["foldseek_alignment"], "fs3")

    @patch("csv.DictReader")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="query\tdescription\nQ1\tdesc1\nQ2\tdesc2\n",
    )
    def test_read_tsv(self, mock_file, mock_dict_reader):
        mock_reader = MagicMock()
        mock_reader.__iter__.return_value = iter(
            [
                {"query": "Q1", "description": "desc1"},
                {"query": "Q2", "description": "desc2"},
            ]
        )
        mock_reader.fieldnames = ["query", "description"]
        mock_dict_reader.return_value = mock_reader

        data, headers = merge_utils.read_tsv("fake.tsv")

        self.assertEqual(data["Q1"]["description"], "desc1")
        self.assertEqual(data["Q2"]["description"], "desc2")
        self.assertEqual(headers, ["query", "description"])

    def test_merge_data(self):
        eggnog_data = {
            "Q1": {"query": "Q1", "desc": "E1_desc", "score": "90"},
            "Q2": {"query": "T|Q2", "desc": "E2_desc", "score": "85"},
            "Q3": {"query": "Q3", "desc": "E3_desc", "score": "70"},
        }
        eggnog_headers = ["query", "desc", "score"]

        foldseek_data = {
            "Q1": {"query": "Q1", "target": "T1", "evalue": "1e-5"},
            "Q2": {"query": "Q2", "target": "T2", "evalue": "2e-3"},
        }
        foldseek_headers = ["query", "target", "evalue"]

        merged_headers, merged_rows = merge_utils.merge_data(
            eggnog_data, eggnog_headers, foldseek_data, foldseek_headers
        )

        expected_headers = [
            "query",
            "eggnog_desc",
            "eggnog_score",
            "foldseek_target",
            "foldseek_evalue",
        ]
        expected_rows = [
            {
                "query": "Q1",
                "eggnog_desc": "E1_desc",
                "eggnog_score": "90",
                "foldseek_target": "T1",
                "foldseek_evalue": "1e-5",
            },
            {
                "query": "Q2",
                "eggnog_desc": "E2_desc",
                "eggnog_score": "85",
                "foldseek_target": "T2",
                "foldseek_evalue": "2e-3",
            },
            # Q3 has no Foldseek hit but is still kept (full outer join),
            # with the Foldseek columns left empty.
            {
                "query": "Q3",
                "eggnog_desc": "E3_desc",
                "eggnog_score": "70",
                "foldseek_target": "",
                "foldseek_evalue": "",
            },
        ]

        self.assertEqual(merged_headers, expected_headers)
        self.assertEqual(merged_rows, expected_rows)


if __name__ == "__main__":
    unittest.main()
