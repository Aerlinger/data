# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import zipfile
from io import BytesIO
from functools import partial
from typing import Any, Dict, List, Tuple

import requests
from tqdm import tqdm
from pandas import DataFrame, Series, read_csv, isnull

from lib.concurrent import thread_map
from lib.net import download
from lib.pipeline import DataSource
from lib.utils import ROOT


class WorldPopPopulationDataSource(DataSource):
    """ Retrieves the requested properties from Wikidata for all items in metadata.csv """

    url_strat_tpl = (
        "ftp://ftp.worldpop.org.uk/GIS"
        "/AgeSex_structures/Global_2000_2020/2020/"
        "{code}/{code_lower}_{sex}_{age_bucket}_2020.tif"
    )

    url_total_tpl = (
        "ftp://ftp.worldpop.org.uk/GIS"
        "/Population/Global_2000_2020/2020/{code}/{code_lower}_ppp_2020.tif"
    )

    # A bit of a circular dependency but we need the latitude and longitude to compute this data
    def fetch(self, cache: Dict[str, str], fetch_opts: Dict[str, Any]) -> List[str]:
        return [ROOT / "output" / "tables" / "geography.csv"]

    def parse_dataframes(
        self, dataframes: List[DataFrame], aux: Dict[str, DataFrame], **parse_opts
    ):
        country_codes = aux["country_codes"]["3166-1-alpha-3"].unique()
        data = aux["country_codes"]
        data["worldpop_population_map"] = data["3166-1-alpha-3"].apply(
            lambda x: self.url_total_tpl.format(code=x, code_lower=x.lower())
        )

        sex_map = {"male": "m", "female": "f"}
        age_map = {f"age_{i * 5:02d}_{(i+ 1) * 5:02d}": f"{i * 5:02d}" for i in range(80 // 5)}
        age_map["age_80_99"] = "80"

        for sex_label, sex_path in sex_map.items():
            for age_bucket, age_path in age_map.items():
                data[f"worldpop_population_map_{sex_label}_{age_bucket}"] = data[
                    "3166-1-alpha-3"
                ].apply(
                    lambda x: self.url_strat_tpl.format(
                        code=x, code_lower=x.lower(), sex=sex_path, age_bucket=age_path
                    )
                )

        return data
