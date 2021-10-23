This script is processing changeset planet file and gives statistics how StreetComplete is used.

It processes metada of all changesets ever made and lists interesting ones (made with Streetcomplete) into csv file for further analysis.

# Disclaimer

This script is published as-is, it was used solely by author.

Feel free to open PRs or create issues if something may be improved to make it more useful for you.

# Hardware requirements

Unlike importing full planet, processing this file has minimal hardware requirements.

Some free space will be required (40 GB should be enough - as of early 2020), PHP to run script.

Usage of RAM and CPU is minimal as file is processed line by line and contains only metadata of changesets. Requirements here are lower than using a web browser for browsing typical bloated web site.

# Output

Written to `output.csv` file. It will contain list of changesets with relevant data, in form easier for further processing.

For StreetComplete it can be easily open in LibreOffice and analysed with pivot tables.

```
changeset_id,editor,changed_objects,quest_type,user_id
44058565,StreetComplete,1,AddOpeningHours,1205786
44059759,StreetComplete,1,AddOpeningHours,1205786
44067748,StreetComplete,1,AddOpeningHours,1205786
(...)
```

Script will also print to output statistics about total edits done per quest type.

# Usage

## Obtaining input data
In my experience torrenting is preferred method, it downloads data very quickly.

### Torrenting

`aria2c https://planet.osm.org/planet/changesets-latest.osm.bz2.torrent`

This will donwload data and continue seeding allowing others to download it.

Use `--seed-time=0` parameter to stop seeding after download.

### Download

Changeset file can be downloaded from [https://planet.osm.org/](https://planet.osm.org/)

In this case "Latest Weekly Changesets" file is needed. It is not huge and can be easily processed line by line.

It can be downloaded using `curl` from one of [mirrors](https://wiki.openstreetmap.org/wiki/Planet.osm#Downloading), for example

`curl -o changesets-latest.osm.bz2 https://ftp.nluug.nl/maps/planet.openstreetmap.org/planet/changesets-latest.osm.bz2`

This one may start slowly, but later it gets faster and completes download in about 45 minutes to download 3.2 GB file, what is faster than ones listed below - at least for me.

or

`curl -o changesets-latest.osm.bz2 https://ftp.osuosl.org/pub/openstreetmap/planet/changesets-latest.osm.bz2`

or

`curl -o changesets-latest.osm.bz2 https://free.nchc.org.tw/osm.planet/planet/changesets-latest.osm.bz2`

Note that curling from the official planet site directly is likely to be flustrating, as it redirects first from `changesets-latest` to specific date and then to one of mirrors.

### Unpack

The file should be unarchived to allow processing, with something like `bzip2 -dk changesets-latest.osm.bz2`.

Unpacking requires 34 GB, as of early 2020.


### Optional using just latest data

`tail -n 2000000` may be used to extract just group of last changesets - in late 2019 it was about one week of activity.

## Running script

`php line_by_line.php "/location_of_input_file/changesets-latest.osm"`

Note that as written it is merging data for StreetComplete and its fork Zażółć (this private fork is used by a single but quite active user). Depending on what you want to achieve you may want to modify script to remove this merge.

## Results

It will write to `output.csv` file in format making futher processing easy. It will also show in the stdout very basic statistics collected during run.

# changesets-latest file

Data in the file looks like this

```
 <changeset id="71993917" created_at="2019-07-08T00:10:48Z" closed_at="2019-07-08T00:32:20Z" open="false" user="Jofe Graham-Jenkins" uid="9581609" min_lat="-21.0791870" min_lon="149.2141598" max_lat="-21.0791870" max_lon="149.2141598" num_changes="1" comments_count="0">
  <tag k="source" v="survey"/>
  <tag k="comment" v="Add opening hours"/>
  <tag k="created_by" v="StreetComplete 12.2"/>
  <tag k="StreetComplete:quest_type" v="AddOpeningHours"/>
 </changeset>
```

or

```
<changeset id="35" created_at="2005-05-24T16:49:34Z" closed_at="2005-05-24T19:28:22Z" open="false" user="Magne" uid="204" min_lat="62.6301994" min_lon="6.1912751" max_lat="63.4497032" max_lon="11.1394958" num_changes="303" comments_count="0"/>
```

for early changesets without tags.

# See also 

[https://github.com/amandasaurus/2021-osm-street-complete-edits](https://github.com/amandasaurus/2021-osm-street-complete-edits) - scripts for finding out how many people have used StreetComplete to edit OSM in an area 
