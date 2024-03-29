This script is processing a changeset planet file and gives statistics on how [StreetComplete](https://github.com/streetcomplete/StreetComplete) is used.

It processes metadata of all changesets ever made and lists interesting ones (=made with StreetComplete) into a CSV file for further analysis.

If you are looking for data about a single user or small number of users then [wielandb/StreetCompleteNumbers](https://github.com/wielandb/StreetCompleteNumbers) that queries OSM API for edits by specific user may be superior.

# Summary

Explanation and variants in sections below.

```sh
# go to the location where data should be processed (replace path as needed)
cd /media/mateusz/OSM_cache/changesets

# get data and start seeding
aria2c https://planet.osm.org/planet/changesets-latest.osm.bz2.torrent

# unpack
bzip2 -dk changesets-*.osm.bz2

# get just latest data
tail -n 2000000 changesets-*.osm > just_latest_changesets.osm
# Note that using tail will likely result in one partially included changeset data, with values ending as -1 in produced CSV files.
# TODO: maybe skip such entries and log that?

# actually run script, from where script is (modify path as needed)
php streetcomplete_edits_generate_csv_and_make_quest_summary.php "/media/mateusz/OSM_cache/changesets/just_latest_changesets.osm"

# transform all edits ever made into a csv file
php all_edits_to_csv_file.php "/media/mateusz/OSM_cache/changesets/changesets-*.osm"
```

# Output

## streetcomplete_edits_generate_csv_and_make_quest_summary.php

Reads data and filters to include just StreetComplete edits.

Written to `output.csv` file. Output is in CSV for further processing.

For StreetComplete it can be easily opened in LibreOffice and analysed with pivot tables.

Contains

* changeset_id
* editor
* how many objects were affected
* quest_type
* user_id


```csv
changeset_id,editor,changed_objects,quest_type,user_id
44058565,StreetComplete,1,AddOpeningHours,1205786
44059759,StreetComplete,1,AddOpeningHours,1205786
44067748,StreetComplete,1,AddOpeningHours,1205786
(...)
```

The script will also print to output statistics about total edits done per quest type.


## usage_by_user_and_quest.php

Loads CSV file generated by the previous script. And generates basic info about how many different people solved given quest type and median of edited elements among them.

## all_edits_to_csv_file.php

Generates CSV with basic info, all edits are included. Also ones made with other editors.

Contains

* changeset_id
* created_by tag (raw form, likely with version info)
* when changeset was created
* how many objects were affected
* user_id

```csv
changeset_id,created_by,creation_date,changed_objects,user_id
112350666,"Level0 v1.2",2021-10-10T22:27:07Z,0,3476229
112350667,"StreetComplete 35.0",2021-10-10T22:27:08Z,10,5687816
112350668,"StreetComplete 35.0",2021-10-10T22:27:09Z,2,5687816
```

# show_usage_stats_by_user.py

Generates an image from provided data which editing chronology of random samples of mappers.

Each pixel is a day of a single mapper.

Each row is a a chronological story of a single mapper, with earlier days to the left and later to the right.

Each column is a specific day.

Colour of each pixel indicates whether they mapped or not

* gray pixel: user have not yet started mapping
* green one: user mapped only with StreetComplete
* white one: user mapped - both with StreetComplete and something else
* blue pixel: user mapped and no edit was made using StreetComplete
* black one: user mapped before but not on this day

Generates samples - from entire population of mappers and from just StreetComplete mappers.

# Dependencies

PHP is needed to run scripts.

``show_usage_stats_by_user.py` requires Python.

# Hardware requirements

Unlike importing full planet, processing this file has minimal hardware requirements.

Some free space will be required. But just 60 GB should be enough - as of 2021.

As of 2023 - compressed file is 5.5 GB.

Usage of RAM and CPU is minimal as file is processed line by line and contains only metadata of changesets. Requirements here are lower than using a web browser for browsing a typical bloated web site.

# Usage

## Obtaining input data
In my experience torrenting is the preferred method as it downloads data very quickly.

### Torrenting

`aria2c https://planet.osm.org/planet/changesets-latest.osm.bz2.torrent`

This will download data and continue seeding allowing others to download it.

Add also `--seed-time=0` parameter to stop seeding after download. But in this case seeding is perfectly legal and helps OSM a bit.

Downloaded within minutes.

### Curl

The changeset file can be downloaded from [https://planet.osm.org/](https://planet.osm.org/)

In this case the "Latest Weekly Changesets" file is needed. It is not huge and can be easily processed line by line.

It can be downloaded using `curl` from one of [mirrors](https://wiki.openstreetmap.org/wiki/Planet.osm#Downloading), for example:

`curl -o changesets-latest.osm.bz2 https://ftp.nluug.nl/maps/planet.openstreetmap.org/planet/changesets-latest.osm.bz2`

+This one may start slowly, but later it gets faster and completes the download of a 3.2 GB file in about 45 minutes, which was faster than the ones listed below - at least for me.

or

`curl -o changesets-latest.osm.bz2 https://ftp.osuosl.org/pub/openstreetmap/planet/changesets-latest.osm.bz2`

or

`curl -o changesets-latest.osm.bz2 https://free.nchc.org.tw/osm.planet/planet/changesets-latest.osm.bz2`

Note that curling from the official planet site directly is likely to be frustrating, as it redirects first from `changesets-latest` to a specific date and then to one of mirrors.

### Unpack

The file should be unarchived to allow processing, with something like `bzip2 -dk changesets-latest.osm.bz2`

`bzip2 -dk changesets-*.osm.bz2` is useful when you have single file with a specific date in filename.


### Optional using just latest data

`tail -n 2000000` may be used to extract just group of last changesets - in late 2021 it was about one week of activity.

Note that it is safe as each change is in its own line and this script parses input line by line and does not need a valid XML as input.

## Running script

`php streetcomplete_edits_generate_csv_and_make_quest_summary.php "/location_of_input_file/changesets-latest.osm"`

Note that as written it is merging data for StreetComplete and its fork Zażółć (this private fork is used by a single but quite active user). Depending on what you want to achieve you may want to modify script to remove this merge.

## Results

It will write to file `output.csv` in CSV format making further processing easy. It will also show very basic statistics collected during execution on stdout.

# changesets-latest file

Data in the file looks like this

```xml
 <changeset id="71993917" created_at="2019-07-08T00:10:48Z" closed_at="2019-07-08T00:32:20Z" open="false" user="Jofe Graham-Jenkins" uid="9581609" min_lat="-21.0791870" min_lon="149.2141598" max_lat="-21.0791870" max_lon="149.2141598" num_changes="1" comments_count="0">
  <tag k="source" v="survey"/>
  <tag k="comment" v="Add opening hours"/>
  <tag k="created_by" v="StreetComplete 12.2"/>
  <tag k="StreetComplete:quest_type" v="AddOpeningHours"/>
 </changeset>
```

or

```xml
<changeset id="35" created_at="2005-05-24T16:49:34Z" closed_at="2005-05-24T19:28:22Z" open="false" user="Magne" uid="204" min_lat="62.6301994" min_lon="6.1912751" max_lat="63.4497032" max_lon="11.1394958" num_changes="303" comments_count="0"/>
```

for early changesets without tags.

# See also

[https://github.com/amandasaurus/2021-osm-street-complete-edits](https://github.com/amandasaurus/2021-osm-street-complete-edits) - scripts for finding out how many people have used StreetComplete to edit OSM in some area

# Disclaimer

This script is published as-is. It was used solely by the author as far as the author knows (PR removing that disclaimer is welcome if you used it succesfully).

Feel free to open PRs or create issues if something may be improved to make it more useful for you.
