#!/usr/bin/env python

'''
This script loads the XLS file from argument and aggregates the data. It also
extracts the last day of data into its own dataset. The output is saved both
in CSV and JSON format under the `output` folder.
'''

import os
import sys
import pandas as pd
from io import BytesIO
from pathlib import Path
import tempfile

# Root path of the project
ROOT = Path(os.path.dirname(__file__)) / '..'

# Read XLS file from stdin
df = pd.read_excel(BytesIO(sys.stdin.buffer.read())).sort_values(['DateRep', 'GeoId'])

# Ensure date field is used as a string
df['DateRep'] = df['DateRep'].astype(str)

# Workaround for https://github.com/open-covid-19/data/issues/8
# ECDC mistakenly labels Greece country code as EL instead of GR
df['GeoId'] = df['GeoId'].apply(lambda code: 'GR' if code == 'EL' else code)

# Workaround for https://github.com/open-covid-19/data/issues/13
# ECDC mistakenly labels Greece country code as UK instead of GB
df['GeoId'] = df['GeoId'].apply(lambda code: 'GB' if code == 'UK' else code)

# Compute the cumsum of values
columns = ['DateRep', 'GeoId', 'Confirmed', 'Deaths']
df_ = pd.DataFrame(columns=columns)
for country in df['GeoId'].unique():
    subset = df[df['GeoId'] == country].copy()
    subset['Confirmed'] = subset['Cases'].cumsum()
    subset['Deaths'] = subset['Deaths'].cumsum()
    df_ = pd.concat([df_, subset[columns]])

df_ = df_[columns]
df_.columns = ['Date', 'CountryCode', 'Confirmed', 'Deaths']
df = df_

# Make sure all data types are appropriately casted
df['Confirmed'] = df['Confirmed'].fillna(0).astype(int)
df['Deaths'] = df['Deaths'].fillna(0).astype(int)

# Temporary workaround for https://github.com/open-covid-19/data/issues/12
# ECDC reported only 90 new cases for Italy, which is clearly wrong. For all
# other days, it appears to report only active cases so we are reporting
# today's active case count from the local official source to avoid a sudden
# jump in the data but this will be fixed retroactively
# https://web.archive.org/web/20200316021137/http://www.salute.gov.it/nuovocoronavirus
df = df.set_index(['Date', 'CountryCode'])
df.loc[('2020-03-15', 'IT'), 'Confirmed'] = 20603
df = df.reset_index()

# Load coordinates and names for each country
# Data from: https://developers.google.com/public-data/docs/canonical/countries_csv
df = df.merge(pd.read_csv(ROOT / 'input' / 'country_coordinates.csv', dtype=str))

# Sort dataset by date + country
df = df.sort_values(['Date', 'CountryCode'])
df = df[['Date', 'CountryCode', 'CountryName', 'Confirmed', 'Deaths', 'Latitude', 'Longitude']]

# Extract a subset with only the latest date
df_latest = pd.DataFrame(columns=list(df.columns))
for country in df['CountryCode'].unique():
    df_latest = pd.concat([df_latest, df[df['CountryCode'] == country].iloc[-1:]])

# Save dataset in CSV format into output folder
df.to_csv(ROOT / 'output' / 'world.csv', index=False)
df_latest.to_csv(ROOT / 'output' / 'world_latest.csv', index=False)

# Save dataset in JSON format into output folder
df.to_json(ROOT / 'output' / 'world.json', orient='records')
df_latest.to_json(ROOT / 'output' / 'world_latest.json', orient='records')