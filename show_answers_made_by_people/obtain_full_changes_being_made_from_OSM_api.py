from osm_easy_api import Api
import csv
import sqlite3
import json
import re
import requests
from osm_easy_api.data_classes import Node, Way, Relation, Changeset, OsmChange, Action, Tags

from osm_easy_api.diff import diff_parser
from datetime import datetime
from osm_bot_abstraction_layer import utils
import time
import osm_bot_abstraction_layer.tag_knowledge as tag_knowledge

from xml.etree import ElementTree

# https://github.com/docentYT/osm_easy_api
"""

python3.10 obtain_full_changes_being_made_from_OSM_api.py

"""
# ImportError: cannot import name 'html5lib' from 'pip._vendor' (/usr/lib/python3/dist-packages/pip/_vendor/__init__.py)
# curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
# python3.10 -m pip install --upgrade osm_easy_api

"""
only raw StreetComplete (forks skipped, lying works may be included - but Zażółć and SCEE are not affecting results)

# get changeset data in csv format, using https://planet.osm.org/
# using https://github.com/matkoniecz/StreetComplete_usage_changeset_analysis#summary
mkdir /media/mateusz/OSM_cache/changesets
git clone https://github.com/matkoniecz/StreetComplete_usage_changeset_analysis.git
cp StreetComplete_usage_changeset_analysis/extracting_data_from_xml_line.php /media/mateusz/OSM_cache/changesets/
cp StreetComplete_usage_changeset_analysis/streetcomplete_edits_generate_csv_and_make_quest_summary.php /media/mateusz/OSM_cache/changesets/
aria2c https://planet.osm.org/planet/changesets-latest.osm.bz2.torrent
bzip2 -dk changesets-*.osm.bz2
tail -n 20000000 changesets-*.osm > just_latest_changesets.osm
php streetcomplete_edits_generate_csv_and_make_quest_summary.php "/media/mateusz/OSM_cache/changesets/just_latest_changesets.osm"

mv /media/mateusz/OSM_cache/changesets/output.csv /media/mateusz/OSM_cache/changesets/sc_edits_list_from_2021-05-20_to_2023-02-20.csv

open csv file
create database and save there replies from API

changeset 117645886 - zrobiony 20 II 2022


List (for example) quests asking whether ATM is still existing

List (for example) bicycle parking capacity changes ever made by StreetComplete mappers

Load history of affected objects

Check whether it was resurvey
Check has it resulted in changes or just marking it as surveyed

Collect statistic
Maybe some quests should be asked  less often (as mistakes are not being actually found). Or more often as many resurveys found outdated data

https://github.com/streetcomplete/StreetComplete/commit/92c6104a164d19d8ee906e0847774d278ecda6cb
"""

def serialize_element_list(input):
    returned = []
    for entry in input:
        returned.append(entry.to_dict())
    return json.dumps(returned, default=str, indent=3)

def deserialize_element_list(serialized):
    # pickling is unsafe
    # "It is possible to construct malicious pickle data which will execute arbitrary code during unpickling."
    # https://docs.python.org/3/library/pickle.html
    # it means that unpickling object with maliciously crafted tags could run `rm -rf /` or worse
    # therefore it is necessary to build own serialization and deserialization
    returned = []
    for entry in serialized:
        if entry['type'] == "Node":
            returned.append(Node.from_dict(entry))
        elif entry['type'] == "Way":
            returned.append(Way.from_dict(entry))
        elif entry['type'] == "Relation":
            returned.append(Relation.from_dict(entry))
        else:
            raise Exception("unexpected type " + entry['type'])
    return returned

def selftest(cursor):
    assert(is_any_of_expected_quests(["addr:housenumber"]))
    api = Api(url='https://openstreetmap.org')

    url = "https://api.openstreetmap.org/api/0.6/way/250066046/history"
    response = requests.get(url=url)
    print(response.content)
    print(response.status_code)
    #print (dir(response))
    api.elements.history(Way, 250066046)
    failed_once = api.elements.get(Way, 250066046)
    history_api_call(api, failed_once)

    node = api.elements.get(Node, 25733488)
    dict = node.to_dict()
    node_from_dict = Node.from_dict(dict)

    node = Node.from_dict({
            'type': "Node",
            'id': 3828631078,
            'visible': True,
            'version': 1,
            'changeset_id': 35212918, # inconsistent :(
            'timestamp': "2015-11-10T13:43:27Z",
            'user_id': 35560, # inconsistent :(
            'tags': {'emergency': 'life_ring'},
            'latitude': 48.7403031,
            'longitude': 9.2906897,
        })
    node.to_dict()

    # edit and undo split into separate edits
    analyse_history(cursor, api, '118933758', 'CheckExistence', {})

    changeset_metadata(cursor, api, 70867569)

    assert(is_one_of_shop_associated_keyes_removed_on_replacement('cuisine') == True)
    assert(is_one_of_shop_associated_keyes_removed_on_replacement('gibberish') == False)
    assert(is_shop_retagging(['amenity'], ['cuisine']) == True)

    for quest in expected_tag_groups().keys():
        if "cuisine" in expected_tag_groups()[quest]:
            raise Exception("not expected")

    for quest in expected_tag_groups().keys():
       for key in expected_tag_groups()[quest]:
        if "signed" in key:
            #  or "check_date" in key
            # is not valid, see opening hours: if check date is there, then it will be updated
            raise Exception("not expected")

    nsi_url = "https://raw.githubusercontent.com/osmlab/name-suggestion-index/main/dist/presets/nsi-id-presets.json"
    r = requests.get(url=nsi_url)
    nsi_data = r.json()
    nsi_data = nsi_data['presets']
    missing = []
    for entry in nsi_data:
        for key in nsi_data[entry]['addTags']:
            if(is_any_key_added_by_nsi(key) == False):
                if key not in missing:
                    missing.append(key)
    if len(missing) > 0:
        print(missing)
        raise Exception("NSI added new keys")

def specific_test_cases(cursor):
    deleting_points = 133235020
    deleting_areas = 133234704
    tag_edit = 133266712
    # https://www.openstreetmap.org/changeset/133522260
    splitting_ways_and_adding_tags = 133522260
    deletion_undone_in_the_separate_changeset = 126057446

    api = Api(url='https://openstreetmap.org')

    analyse_history(cursor, api, deletion_undone_in_the_separate_changeset, 'CheckExistence', {})

def main():
    connection = sqlite3.connect(database_filepath())
    cursor = connection.cursor()
    create_table_if_needed(cursor)
    check_database_integrity(cursor)
    selftest(cursor)
    connection.commit()
    specific_test_cases(cursor)

    api = Api(url='https://openstreetmap.org')
    #prefetch_data(connection, api, cursor, standard_is_quest_of_interest)
    produce_statistics_info(connection, api, cursor, standard_is_quest_of_interest)
    prefetch_data(connection, api, cursor, wider_is_quest_of_interest)
    prefetch_data(connection, api, cursor, accept_all)
    connection.close()

def accept_all(quest_type, changeset_id):
    return True

def wider_is_quest_of_interest(quest_type, changeset_id):
    if changeset_id < 117645886:
        return False
    if changeset_id % 1000 <= 4:
        return True
    return standard_is_quest_of_interest(quest_type, changeset_id)

def standard_is_quest_of_interest(quest_type, changeset_id):
    if changeset_id < 117645886:
        return False
    return quest_type in ["CheckExistence", "AddOpeningHours", "AddFireHydrantDiameter"]

def prefetch_data(connection, api, cursor, is_quest_of_interest):
    edit_count = 4553747
    processed = 0
    skipped = 0
    # prefetch, with low CPU use
    with open('/media/mateusz/OSM_cache/changesets/sc_edits_list_from_2021-05-20_to_2023-02-20.csv') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)
        for row in reader:
            changeset_id = int(row[0])
            quest_type = row[3]
            processed += 1
            if is_quest_of_interest(quest_type, changeset_id):
                for element in elements_edited_by_changeset(cursor, api, changeset_id):
                    object_history(cursor, api, changeset_id, element)
                connection.commit()
            else:
                skipped += 1
                continue
            if changeset_id % 2000 == 0:
                show_progress(processed, skipped, edit_count)

def produce_statistics_info(connection, api, cursor, is_quest_of_interest):
    stats = []
    missing_tag_usage = {}
    last_edit_id = 132770010
    edit_count = 4553747
    processed = 0
    skipped = 0
    with open('/media/mateusz/OSM_cache/changesets/sc_edits_list_from_2021-05-20_to_2023-02-20.csv') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)
        for row in reader:
            changeset_id = int(row[0])
            processed += 1
            editor = row[1]
            quest_type = row[3]
            if is_quest_of_interest(quest_type, changeset_id):
                stats += analyse_history(cursor, api, changeset_id, quest_type, missing_tag_usage)
            else:
                skipped += 1
                continue
            connection.commit()
            if changeset_id % 2000 == 0:
                show_progress(processed, skipped, edit_count)
            if len(stats) % 10_000 == 0:
                print("updating CSV file on", len(stats))
                write_csv_file(stats, "in_progress")
    write_csv_file(stats, "some")

def show_progress(processed, skipped, edit_count):
    print()
    #print("out of", edit_count, "processed", processed, "inluding", skipped, "skipped")
    percent_done = (processed - skipped) * 100 / (edit_count - skipped)
    print('{0:.2f}'.format(percent_done), "% done", str(int((processed - skipped)/1000)) + "k out of " + str(int((edit_count - skipped)/1000)) + "k")
    print()

def write_csv_file(stats, title):
    todocount = 0
    with open('/media/mateusz/OSM_cache/cache-for-osm-editing-api/' + title + '.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        for entry in stats:
            if '????TODO' in entry['action']:
                todocount += 1
            else:
                if 'days' in entry:
                    writer.writerow([entry["quest_type"], entry["action"], entry["days"], entry["main_tag"], entry["link"]])
                else:
                    print("Missing day entry, skipping", entry["link"])
                    print(entry)
    print(todocount, 'unhandled entries')


def get_main_key_from_tags(tags):
    for potential_main_key in tag_knowledge.typical_main_keys():
        if potential_main_key in tags:
            return potential_main_key + " = " + tags[potential_main_key]
    #return "wat=wat" # TODO investigate
    # {'addr:city': 'Siegen', 'addr:country': 'DE', 'addr:housenumber': '16', 'addr:postcode': '57076', 'addr:street': 'Wilhelm-von-Humboldt-Platz', 'email': 'info@service-transport.de', 'mobile': '+49 152 51427455', 'name': 'S-Transport Haushaltsauflösungen & Entrümpelungen in Siegen', 'opening_hours': 'Mo-Fr 08:00-20:00, Sa 08:00-18:00', 'phone': '+49 271 23571842', 'website': 'https://www.service-transport.de'}
    print("main tag - failed to find for ", tags)
    return None

def analyse_history(local_database_cursor, api, changeset_id, quest_type, missing_tag_usage):
    new_stats = []
    for element in elements_edited_by_changeset(local_database_cursor, api, changeset_id):
        history = object_history(local_database_cursor, api, changeset_id, element)
        link = "https://www.openstreetmap.org/" + type(element).__name__.lower() + "/" + str(element.id) + "/history"
        changeset_link = "https://www.openstreetmap.org/changeset/" + str(changeset_id)
        for index, entry in enumerate(history):
            if entry.changeset_id == changeset_id:
                # multiple changes to a single object within a single changeset are possible
                # with an undo
                # in such case what should be done?
                # register undone as undone?
                # register reverts as reverts?
                # register last one as applying if it is not just revert to the initial state?
                #
                # note that nodes can be also moved! Maybe even multiple times.
                # so not only reverts
                #
                # and it is possible to combine them...
                # moving node may mean that it is revert of node move
                #
                # ideally history would be better supported here...
                # TODO - support this!

                # it gets worse! splits across multiple changesets are possible with delayed undos!
                # TODO - support this!
                for index_of_potential_duplicate, potential_duplicate_entry in enumerate(history):
                    if index != index_of_potential_duplicate:
                        if entry.changeset_id == potential_duplicate_entry.changeset_id: # new_stats != []
                            print()
                            print(quest_type)
                            print(link)
                            print(changeset_link)
                            print("entry.changeset_id == potential_duplicate_entry.changeset_id")
                            print(entry.changeset_id, potential_duplicate_entry.changeset_id)
                            print("handle revert within single edit (just take latest action)")
                            new_stats.append({"quest_type": quest_type, "action": '????TODO', 'main_tag': None, 'link': link})
                            # TODO: handling do-revert-do_something_else (right now all three would be treated as reverts)
                            print("our index:", index, "other index:", index_of_potential_duplicate)
                            print("our version:", index+1, "other version:", index_of_potential_duplicate+1)
                            print("But it can be also way splitting, or moving objects and then aswering question...")
                            if index < index_of_potential_duplicate:
                                print("edit before final edit, lets skip it - but do not exit this function (or extract checking specific revision?)")
                            else:
                                print("final edit, lets handle it - but has it made change compared to the initial state? Or just reverted and updated last edit time?")
                            # interesting cases
                            # https://www.openstreetmap.org/node/7188433530/history
                            # https://www.openstreetmap.org/changeset/126653302 has r3 and r5 but not r4
                            return new_stats
                        if entry.user_id == potential_duplicate_entry.user_id:
                            timestamp = datetime.strptime(entry.timestamp, utils.typical_osm_timestamp_format())
                            other_timestamp = datetime.strptime(potential_duplicate_entry.timestamp, utils.typical_osm_timestamp_format())
                            if abs((timestamp - other_timestamp).days) < 2: # TODO check real data!
                                changeset_tags = changeset_metadata(local_database_cursor, api, entry.changeset_id).tags
                                potential_duplicate_changeset_tags = changeset_metadata(local_database_cursor, api, potential_duplicate_entry.changeset_id).tags
                                if 'comment' in potential_duplicate_changeset_tags:
                                    if changeset_tags['comment'] == potential_duplicate_changeset_tags['comment']:
                                        print()
                                        print("---------------------------------<")
                                        print(quest_type)
                                        print()
                                        print(link)
                                        print(changeset_link)
                                        print("Requires smarter check, possible revert")
                                        print("Is position the same?")
                                        print("Are tags the same?")
                                        print("If the same then it may be edit-revert-the same edit!")
                                        print("Some may be the same due to this duplication bug")
                                        print(timestamp)
                                        print(other_timestamp)
                                        print(changeset_metadata(local_database_cursor, api, entry.changeset_id))
                                        print(entry.tags)
                                        latitude = None
                                        longitude = None
                                        if type(element).__name__.lower() == "node":
                                            latitude = entry.latitude
                                            longitude = entry.longitude
                                        print(latitude, longitude)

                                        print(changeset_metadata(local_database_cursor, api, potential_duplicate_entry.changeset_id))
                                        print(potential_duplicate_entry.tags)
                                        potential_duplicate_latitude = None
                                        potential_duplicate_longitude = None
                                        if type(element).__name__.lower() == "node":
                                            potential_duplicate_latitude = potential_duplicate_entry.latitude
                                            potential_duplicate_longitude = potential_duplicate_entry.longitude
                                        print(potential_duplicate_latitude, potential_duplicate_longitude)
                                        # smarter checks: blocked by https://github.com/docentYT/osm_easy_api/issues/7 for now
                                        new_stats.append({"quest_type": quest_type, "action": '????TODO - the same user, assuming the same action', 'main_tag': None, 'link': link})
                                        print(">---------------------------------")
                                        return new_stats
                if index == 0:
                    new_stats.append({"quest_type": quest_type, "action": 'created', 'main_tag': get_main_key_from_tags(entry.tags), 'link': link})
                else:
                    previous_entry = history[index - 1]
                    if previous_entry.visible == False:
                        print("StreetComplete is undoing deletion here, this was split into multiple edits. How to handle THAT? TODO")
                        new_stats.append({"quest_type": quest_type, "action": '????TODO', 'main_tag': None, 'link': link})
                    else:
                        this_timestamp = datetime.strptime(entry.timestamp, utils.typical_osm_timestamp_format())
                        previous_timestamp = datetime.strptime(previous_entry.timestamp, utils.typical_osm_timestamp_format())
                        days = (this_timestamp - previous_timestamp).days
                        #print(days, "days")
                        #print(previous_entry.tags)
                        #print(link)
                        main_tag = get_main_key_from_tags(previous_entry.tags)
                        if entry.visible == False:
                            latitude = None
                            longitude = None
                            if type(element).__name__.lower() == "node":
                                latitude = previous_entry.latitude
                                longitude = previous_entry.longitude
                            new_stats.append({"quest_type": quest_type, "action": 'deleted', 'days': days, 'main_tag': main_tag, 'link': link})
                            #print("DELETED")
                        else:
                            #handle ways and relations
                            latitude = None
                            longitude = None
                            if type(element).__name__.lower() == "node":
                                latitude = entry.latitude
                                longitude = entry.longitude
                            change_summary = affected_tags(entry, previous_entry)
                            streetcomplete_tagged = change_summary['added'] + change_summary['modified']
                            if is_shop_retagging(streetcomplete_tagged, change_summary['removed']):
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif only_check_dates_or_sign_presence_here(streetcomplete_tagged):
                                #print("MARKED AS STILL EXISTING")
                                # includes say fire_hydrant:diameter:signed
                                new_stats.append({"quest_type": quest_type, "action": 'marked_as_surveyed', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif "disused:shop" in streetcomplete_tagged:
                                # flipped shop type, probably
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif is_any_of_expected_quests(streetcomplete_tagged):
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})                            
                            else:
                                print()
                                print("NOT HANDLED", quest_type)
                                print(streetcomplete_tagged, change_summary['removed'])
                                print(link)
                                print(changeset_link)
                                if quest_type not in missing_tag_usage:
                                    missing_tag_usage[quest_type] = set()

                                for key in streetcomplete_tagged:
                                    if key not in missing_tag_usage[quest_type]:
                                        missing_tag_usage[quest_type].add(key)
    

                                known_affected = expected_tag_groups()
                                for key in missing_tag_usage.keys():
                                    if key not in known_affected:
                                        known_affected[key] = []
                                    merged = list(set(list(known_affected[key] + list(missing_tag_usage[key])))) # TODO
                                    known_affected[key] = merged

                                for key in known_affected:
                                    print('        "' + key + '": ' + str(known_affected[key]).replace("'", '"') + ",")
                                print()
                                print()
                #print("==============")
                #print()
    return new_stats

def is_any_of_expected_quests(affected_keys):
    for quest in expected_tag_groups().keys():
        if is_edit_limited_to_this_keys(affected_keys, expected_tag_groups()[quest]):
            return True
    return False


def expected_tag_groups():
    return {
        "AddHousenumber": ["nohousenumber", "addr:housename", "addr:housenumber"],
        "AddOpeningHours": ["opening_hours", "check_date:opening_hours"], # check_date:opening_hours may be updated if present
        "AddBenchStatusOnBusStop": ["bench"],
        "AddRoadWidth": ["width", "source:width"],
        "AddTracktype": ["tracktype"],
        "AddFireHydrantDiameter": ["fire_hydrant:diameter"],
        "AddRoadSurface": ["surface"],
        "AddBuildingType": ["historic", "building", "abandoned"],
        "AddRoadSmoothness": ["smoothness"],
        "AddCycleway": ["cycleway:both:lane", "cycleway:left:lane", "cycleway:both", "cycleway:left:segregated", "cycleway:right", "cycleway:left"],
        "AddParkingAccess": ["access"],
        "AddParkingFee": ["fee"],
        "AddPathSmoothness": ["smoothness"],
        "AddTrafficSignalsSound": ["traffic_signals:sound"],
        "AddBusStopShelter": ["shelter"],
        "AddStepsIncline": ["incline"],
        "AddCyclewayWidth": ["cycleway:width"],
        "AddStepsRamp": ["ramp:stroller", "ramp:wheelchair", "ramp"],
        "AddWheelchairAccessPublicTransport": ["wheelchair"],
        "AddCrossingType": ["crossing"],
        "AddWayLit": ["lit"],
        "AddCrossingIsland": ["crossing:island"],
        "AddAddressStreet": ["addr:street"],
        "AddBicycleBarrierType": ["cycle_barrier"],
        "AddSeating": ["outdoor_seating", "indoor_seating"],
        "AddLanes": ["lane_markings", "lanes:backward", "lanes:forward", "lanes"],
        "AddSidewalk": ["sidewalk"],
        "AddCrossing": ["highway", "kerb"],
        "AddTrafficSignalsButton": ["button_operated"],
        "AddParkingType": ["parking"],
        "AddPowerPolesMaterial": ["material"],
        "SidewalkOverlay": ["sidewalk:left", "sidewalk", "sidewalk:right"],
        "AddHandrail": ["handrail"],
        "AddFireHydrantType": ["fire_hydrant:type"],
        "AddWheelchairAccessToiletsPart": ["toilets:wheelchair"],
        "AddBuildingLevels": ["roof:levels", "building:levels"],
        "AddTactilePavingCrosswalk": ["tactile_paving"],
        "AddBikeParkingCover": ["covered"],
        "AddTactilePavingBusStop": ["tactile_paving"],
        "AddBinStatusOnBusStop": ["bin"],
        "AddTactilePavingKerb": ["tactile_paving"],
        "AddTrafficSignalsVibration": ["traffic_signals:vibration"],
        "AddVegetarian": ["diet:vegetarian"],
        "AddFireHydrantPosition": ["fire_hydrant:position"],
        "AddForestLeafType": ["leaf_type"],
        "AddBridgeStructure": ["bridge:structure"],
        "AddToiletAvailability": ["toilets"],
        "AddKerbHeight": ["kerb", "barrier"],
        "DetermineRecyclingGlass": ["recycling:glass", "recycling:glass_bottles"],
        "AddRoofShape": ["roof:shape"],
        "AddCyclewaySegregation": ["segregated"],
        "AddRecyclingContainerMaterials": ["amenity", "recycling:glass_bottles", "recycling:paper", "recycling:scrap_metal", "recycling:plastic", "recycling:cans", "recycling:green_waste"],
        "AddBollardType": ["bollard"],
        "AddMemorialType": ["memorial"],
        "AddCyclewayPartSurface": ["cycleway:surface"],
        "AddProhibitedForPedestrians": ["foot"],
        "StreetParkingOverlay": ["parking:lane:right", "parking:condition:both", "parking:lane:both", "parking:lane:left", "parking:condition:left", "parking:lane:left:parallel"],
        "AddAirCompressor": ["compressed_air"],
        "AddSidewalkSurface": ["sidewalk:both:surface", "sidewalk:right:surface", "sidewalk:left:surface"],
        "AddBikeParkingType": ["bicycle_parking"],
        "AddBenchBackrest": ["backrest"],
        "AddOneway": ["oneway"],
        "AddShoulder": ["shoulder"],
        "AddStepCount": ["step_count"],
        "AddAirConditioning": ["air_conditioning"],
        "AddRailwayCrossingBarrier": ["crossing:barrier"],
        "AddEntrance": ["entrance"],
        "AddMaxHeight": ["maxheight"],
        "AddCameraType": ["camera:type"],
        "AddAtmCashIn": ["cash_in"],
        "AddStepCountStile": ["step_count"],
        "AddCarWashType": ["self_service", "automated"],
        "AddPostboxRef": ["ref"],
        "AddChargingStationCapacity": ["capacity"],
        "AddHalal": ["diet:halal"],
        "AddKosher": ["diet:kosher"],
        "AddBikeParkingCapacity": ["capacity"],
        "AddVegan": ["diet:vegan"],
        "AddMaxWeight": ["maxweight"],
        "AddMaxSpeed": ["maxspeed", "maxspeed:type"],
        "AddCampDrinkingWater": ["drinking_water"],
    }

def only_check_dates_or_sign_presence_here(affected_keys):
    for key in affected_keys:
        if "check_date" not in key:
            if ":sign" not in key:
                return False
    return True

def is_edit_limited_to_this_keys(affected_keys, expected):
    if affected_keys == []:
        return False
    for key in affected_keys:
        if key not in expected:
            return False
    return True

def is_shop_retagging(affected_keys, deleted_keys):
    # note that shop=clothes name=Foobar -> shop=clothes also counts
    main_found = False
    for key in affected_keys:
        if is_main_key_added_by_nsi(key):
            main_found = True
            continue
        if is_secondary_key_added_by_nsi(key):
            main_found = True
            continue
        return False
    if main_found == False:
        return False
    for key in deleted_keys:
        if is_one_of_shop_associated_keyes_removed_on_replacement(key):
            continue
        if key in [ # LAST_CHECK_DATE_KEYS
            "check_date",
            "lastcheck",
            "last_checked",
            "survey:date",
            "survey_date",
        ]:
            continue
        return False
    return True

def is_any_key_added_by_nsi(key):
    return is_main_key_added_by_nsi(key) or is_secondary_key_added_by_nsi(key)

def is_main_key_added_by_nsi(key):
    return key in ['shop', 'amenity', 'healthcare', 'craft', 'leisure', 'office']

def is_secondary_key_added_by_nsi(key):
    # note https://www.openstreetmap.org/node/429346232/history
    # SC is using NSI and NSI preset has some cases with say cuisine...
    # https://github.com/osmlab/name-suggestion-index/blob/main/dist/presets/nsi-id-presets.json
    # https://raw.githubusercontent.com/osmlab/name-suggestion-index/main/dist/presets/nsi-id-presets.json
    return key in [
        'barnd:en', # NSI bug, see https://github.com/osmlab/name-suggestion-index/commit/8e66b7ee87cc7ced4ff9ff96a6b5606df410d69b
        # for now still in https://raw.githubusercontent.com/osmlab/name-suggestion-index/main/dist/presets/nsi-id-presets.json
        # may be necessary to keep it if ever used by StreetComplete mapper

        'name', 'brand', 'brand:wikidata', 'cuisine', 'animal_boarding',
        'operator', 'operator:wikidata', 'network', 'network:wikidata', 'operator:short',
        'brand:en', 'brand:fa', 'brand:he', 'brand:ru', 'brand:sr', 'brand:sr-Latn', 'name:en',
        'name:sr', 'name:sr-Latn', 'official_name', 'short_name', 'official_name:en', 'name:bg',
        'brand:ur', 'name:ur', 'brand:ar', 'name:ar', 'brand:ca', 'brand:es', 'name:ca', 'name:es',
        'brand:fr', 'name:fr', 'name:el', 'name:tr', 'name:kk', 'name:ru', 'official_name:kk',
        'official_name:ru', 'brand:de', 'name:de', 'short_name:de', 'short_name:fr',
        'official_name:fr', 'short_name:en', 'alt_name', 'alt_name:lb', 'official_name:vi',
        'official_name:ar', 'brand:id', 'brand:hi', 'brand:kn', 'brand:pa', 'brand:pnb', 'name:hi',
        'name:kn', 'name:pa', 'name:pnb', 'brand:ta', 'name:ta', 'name:zh', 'name:zh-Hans',
        'name:zh-Hant', 'brand:bg', 'short_name:bg', 'brand:it', 'name:it', 'short_name:it',
        'name:mk', 'old_name', 'brand:zh', 'brand:ko', 'name:ko', 'alt_name:en', 'brand:ja',
        'name:ja', 'name:hr', 'brand:el', 'short_name:el', 'brand:be', 'name:be', 'alt_name:ru',
        'brand:uk', 'name:uk', 'full_name', 'full_name:en', 'official_name:uk', 'short_name:uk',
        'brand:be-tarask', 'name:be-tarask', 'brand:mn', 'name:mn', 'short_name:ru', 'brand:mk',
        'short_name:mk', 'name:he', 'name:fa', 'name:ks', 'name:sd', 'brand:bn', 'name:bn',
        'brand:th', 'name:th', 'name:ko-Latn', 'name:nan', 'name:nan-HJ', 'name:nan-POJ',
        'name:nan-TL', 'brand:zh-Hans', 'brand:zh-Hant', 'brand:pt', 'name:pt', 'name:hak',
        'food', 'sport', 'bicycle_rental', 'fee', 'operator:type', 'official_name:ja',
        'operator:en', 'operator:ja', 'access', 'network:en', 'network:ja', 'network:uk',
        'authentication:app', 'rental', 'network:zh', 'network:ru', 'network:fa', 'operator:zh',
        'nerwork:zh', 'takeaway', 'name:vi', 'drive_through', 'alt_name:vi', 'brand:vi',
        'int_name', 'alt_name:he', 'alt_name:zh', 'alt_name:ja', 'brand:short', 'after_school',
        'grades', 'nursery', 'preschool', 'healthcare:speciality', 'delivery', 'diet:kosher',
        'short_name:ja', 'diet:vegan', 'diet:halal', 'diet:vegetarian', 'alt_name:hi',
        'alt_name:pa', 'alt_name:pnb', 'alt_name:ur', 'drive_in', 'opening_hours', 'brand:nan',
        'brand:nan-HJ', 'brand:nan-POJ', 'brand:nan-TL', 'ref:vatin', 'hgv', 'fuel:biogas',
        'fuel:discount', 'fuel:LH2', 'payment:cash', 'payment:cfn', 'payment:credit_cards',
        'payment:debit_cards', 'fuel:h70', 'gambling', 'coffee', 'internet_access:fee',
        'isced:level', 'max_age', 'min_age', 'brand:ja-Hira', 'brand:ja-Latn', 'language:en',
        'name:ja-Hira', 'name:ja-Latn', 'language:es', 'short_name:ja-Hira', 'short_name:ja-Latn',
        'alt_name:ja-Latn', 'language:ja', 'language:ko', 'parcel_mail_in', 'parcel_pickup',
        'operator:nan', 'operator:nan-HJ', 'operator:nan-POJ', 'operator:nan-TL', 'operator:zh-Hans',
        'operator:zh-Hant', 'operator:de', 'operator:fr', 'operator:it', 'operator:rm', 'alt_name:bg',
        'payment:alipay_HK', 'payment:octopus', 'payment:payme', 'payment:unionpay', 'payment:wechat',
        'wheelchair', 'brand:ka', 'name:ka', 'brewery', 'brewery:wikidata', 'microbrewery',
        'drink:palm_wine', 'name:wikidata', 'recycling_type', 'recycling:cans', 'recycling:glass_bottles',
        'recycling:plastic_bottles', 'recycling:mobile_phones', 'recycling:clothes', 'recycling:shoes',
        'recycling:low_energy_bulbs', 'name:pronunciation', 'recycling:bags', 'recycling:toys',
        'recycling:books', 'owner', 'owner:en', 'owner:wikidata', 'owner:zh', 'owner:zh-Hans', 'owner:zh-Hant',
        'reservation', 'diet:meat', 'oven', 'breakfast', 'alcohol', 'brand:zn', 'brand:ug', 'name:ug',
        'brand:yue', 'name:yue', 'social_centre:for', 'social_facility', 'social_facility:for',
        'brand:lb', 'operator:lb', 'healthcare:counselling', 'healthcare:for', 'training',
        'drink:soft_drink', 'vending', 'fuel:lpg', 'drink:cola', 'network:guid', 'network:short',
        'bin', 'drink:brewery', 'drink:water', 'drink:tea', 'drink:milk', 'club', 'electronics_repair',
        'name:cs', 'name:sk', 'emergency', 'donation:compensation', 'blood:plasma', 'highway', 'landuse',
        'residential', 'dance:teaching', 'female', 'bar', 'indoor', 'insurance', 'official_name:ja-Latn',
        'agrarian', 'pastry', 'alt_name:ko', 'beauty', 'seamark:small_craft_facility:category',
        'seamark:type', 'books', 'second_hand', 'butcher', 'addr:province', 'service:bicycle:repair',
        'service:bicycle:retail', 'service:vehicle:transmission', 'service:vehicle:body_repair',
        'service:vehicle:painting', 'service:vehicle:glass', 'clothes', 'organic', 'self_service',
        'name:pl', 'payment:app', 'duty_free', 'brand:ms-Arab', 'name:ms-Arab', 'operator:th', 'operator:ko',
        'name:hu', 'furniture', 'male', 'brand:offical_name', 'fair_trade', 'official_name:zh',
        'official_name:zh-Hans', 'official_name:zh-Hant', 'motorcycle:clothes', 'motorcycle:parts',
        'tobacco', 'shoes', 'brand:rs', 'name:np', 'bulk_purchase', 'origin', 'zero_waste',
        'alt_name:ar', 'short_name:nan', 'short_name:nan-HJ', 'short_name:nan-POJ', 'short_name:nan-TL',
        'short_name:zh', 'operator:bg', 'trade', 'tourism', 'internet_access', 'internet_access:operator',
        'internet_access:ssid', 'information', 'map_size', 'map_type', 'country', 'flag:name', 'flag:type',
        'flag:wikidata', 'man_made', 'subject', 'subject:wikidata', 'flag:colour', 'bicycle_parking',
        'bike_ride', 'urgent_care', 'operator:es', 'name:ms', 'operator:official', 'operator:id',
        'operator:he', 'operator:cy', 'ref:isil', 'operator:mi', 'operator:af', 'operator:xh',
        'operator:ga', 'building', 'parking', 'park_ride', 'operator:ar', 'operator:ml',
        'operator:ne', 'operator:pt', 'alt_name:fr', 'operator:hy', 'operator:uk', 'operator:el',
        'operator:be', 'operator:ru', 'colour', 'denomination', 'religion', 'toilets:disposal',
        'currency:PLN', 'payment:coins', 'payment:contactless', 'payment:maestro', 'payment:mastercard',
        'payment:mastercard_electronic', 'payment:notes', 'payment:v_pay', 'payment:visa',
        'payment:visa_electron', 'payment:electronic_purses', 'payment:cards', 'boundary',
        'ownership', 'protected', 'operator:short:en', 'operator:short:zh', 'payment:license_plate',
        'payment:txtag', 'payment:ez_tag', 'payment:tolltag', 'industrial', 'operator:ka', 'operator:or',
        'addr:state', 'operator:bn', 'tower:type', 'tower:construction', 'communication:mobile_phone',
        'substance', 'street_cabinet', 'product', 'natural', 'water', 'government', 'pipeline', 'power',
        'frequency', 'substation', 'operator:short:zh-Hans', 'operator:short:zh-Hant', 'operator:short:pt',
        'route', 'type', 'operator:hak', 'name:signed', 'telecom', 'ferry', 'public_transport', 'bus',
        'network:no', 'network:el', 'network:ko', 'network:nan', 'network:nan-HJ', 'network:nan-POJ',
        'network:nan-TL', 'operator:not', 'network:zh-yue', 'network:metro', 'network:metro:wikidata',
        'public_transport:network', 'public_transport:network:en', 'public_transport:network:wikidata',
        'public_transport:network:zh', 'railway:network', 'railway:network:en', 'railway:network:wikidata',
        'railway:network:zh', 'network:zh-Hans', 'network:zh-Hant', 'network:pt', 'network:es', 'network:eu',
        'operator:eu', 'network:short_name']

def affected_tags(entry, previous_entry):
    #print(previous_entry.tags)
    #print(entry.tags)
    affected = {
        'modified': [],
        'modified_details': [],
        'added': [],
        'removed': [],
    }
    for key in entry.tags.keys():
        if key in previous_entry.tags.keys():
            if entry.tags[key] == previous_entry.tags[key]:
                pass
            else:
                #print("MODIFIED", key, "=", entry.tags[key], "to", key, "=", previous_entry.tags[key])
                affected['modified'].append(key)
                affected['modified_details'].append({
                    'key': key,
                    'old_value': previous_entry.tags[key],
                    'new_value': entry.tags[key]
                })
        else:
            #print("ADDED", key, "=", entry.tags[key])
            affected['added'].append(key)
    for key in previous_entry.tags.keys():
        if key in entry.tags:
            pass
        else:
            #print("REMOVED", key, "=", previous_entry.tags[key])
            affected['removed'].append(key)
    return affected

def elements_edited_by_changeset(local_database_cursor, api, changeset_id):
    local_database_cursor.execute("""
    SELECT element_list
    FROM changeset_object_api_cache
    WHERE changeset_id == :changeset_id
    """, {"changeset_id": changeset_id})
    entries = local_database_cursor.fetchall()
    if len(entries) == 1:
        return deserialize_element_list(json.loads(entries[0][0]))

    element_list = []
    for action in api.changeset.download(changeset_id):
        if action[0] != Action.MODIFY and action[0] != Action.DELETE and action[0] != Action.CREATE:
            print(action)
            raise
        element = action[1]
        element_list.append(element)
    saved_as_json = serialize_element_list(element_list)
    local_database_cursor.execute("INSERT INTO changeset_object_api_cache VALUES (:changeset_id, :element_list)", {"changeset_id": changeset_id, 'element_list': saved_as_json})

    return element_list


def changeset_metadata(local_database_cursor, api, changeset_id):
    local_database_cursor.execute("""
    SELECT serialized
    FROM changeset_metadata_api_cache
    WHERE changeset_id = :changeset_id
    """, {"changeset_id": changeset_id})
    entries = local_database_cursor.fetchall()
    if len(entries) == 1:
        return Changeset.from_dict(json.loads(entries[0][0]))
    if len(entries) > 1:
        print(len(entries))
        print(entries)
        raise

    print("MAKING A CALL TO OSM API - api.changeset.download(", changeset_id, ")")
    downloaded = api.changeset.get(changeset_id)

    serialized = json.dumps(downloaded.to_dict(), default=str, indent=3)
    local_database_cursor.execute("INSERT INTO changeset_metadata_api_cache VALUES (:changeset_id, :serialized)", {"changeset_id": changeset_id, 'serialized': serialized})

    return changeset_metadata(local_database_cursor, api, changeset_id)
    #return Changeset.from_dict(downloaded.to_dict())

def object_history(local_database_cursor, api, for_changeset_id, element_as_osm_easy_api_object):
    element_type_label = type(element_as_osm_easy_api_object).__name__.lower()
    #print(element_type_label)
    local_database_cursor.execute("""
    SELECT serialized_history
    FROM history_api_cache
    WHERE for_changeset_id >= :for_changeset_id AND object_type = :object_type AND object_id = :object_id
    ORDER BY for_changeset_id DESC LIMIT 1
    """, {"for_changeset_id": for_changeset_id, 'object_type': element_type_label, 'object_id': element_as_osm_easy_api_object.id})
    entries = local_database_cursor.fetchall()
    if len(entries) == 1:
        return deserialize_element_list(json.loads(entries[0][0]))

    returned = history_api_call(api, element_as_osm_easy_api_object)
    serialized = serialize_element_list(returned)

    known_changeset = 134282514 # we are fetching after this changeset was created and after all earlier changesets were closed
    # so even if we fetch for earlier changeset, we can trust that data up to changeset  134282514 was fetched
    # TODO fetch latest definitely closed changeset dynamically
    # Why? So if we fetch object history for changeset 4000 at time when changeset 100_000_000 and all earlier are closed
    # then we can use this data also when checking changeset 5000
    if for_changeset_id > known_changeset:
        raise Exception("Time passed, new larger changeset!")
    local_database_cursor.execute("INSERT INTO history_api_cache VALUES (:for_changeset_id, :object_type, :object_id, :serialized_history)", {"for_changeset_id": known_changeset, 'object_type': element_type_label, 'object_id': element_as_osm_easy_api_object.id, 'serialized_history': serialized})

    return returned

def prepare_history_api_call_function(api, element_as_osm_easy_api_object):
    def execute_api_call():
        while True:
            try:
                print("MAKING A CALL TO OSM API - api.elements.history(", type(element_as_osm_easy_api_object).__name__.lower(), ",",  element_as_osm_easy_api_object.id, ")")
                return api.elements.history(element_as_osm_easy_api_object.__class__, element_as_osm_easy_api_object.id)
            except ElementTree.ParseError: # https://github.com/docentYT/osm_easy_api/issues/9
                url = "https://api.openstreetmap.org/api/0.6/" + type(element_as_osm_easy_api_object).__name__.lower() + "/" + str(element_as_osm_easy_api_object.id) + "/history"
                response = requests.get(url=url)
                print(response)
                print(response.status_code)
                # https://github.com/zerebubuth/openstreetmap-cgimap/blob/master/src/process_request.cpp#L521
                # https://github.com/zerebubuth/openstreetmap-cgimap/blob/3482ee87da44cd016c5de2b9dfb1cece663dd006/include/cgimap/rate_limiter.hpp#L1
                # https://github.com/zerebubuth/openstreetmap-cgimap/blob/3482ee87da44cd016c5de2b9dfb1cece663dd006/src/rate_limiter.cpp#L4
                print("RETRY! BUT FIRST SLEEP FOR 1H")
                time.sleep(3600)
                print("RETRY")
    return execute_api_call

def history_api_call(api, element_as_osm_easy_api_object):
    while True:
        try:
            api_call = prepare_history_api_call_function(api, element_as_osm_easy_api_object)
            return api_call()
        except requests.exceptions.ConnectionError as e:
            print(e)
            sleep_before_retry("requests.exceptions.ConnectionError")
            continue
        except requests.exceptions.HTTPError as e:
            print(e.response.status_code)
            raise e
        except requests.exceptions.ReadTimeout as e:
            time_now = time.time()
            time_used_for_query_in_s = time_now - time_of_query_start
            failure_explanation = "timeout (after " + str(time_used_for_query_in_s) + ", timeout passed to query was " + str(timeout) + " - if it is None then it defaulted to some value)"
            sleep_before_retry(failure_explanation)
            continue
        except requests.exceptions.ChunkedEncodingError as e:
            print(e)
            sleep_before_retry("requests.exceptions.ChunkedEncodingError")
            continue

def sleep_before_retry(error_summary):
    print("sleeping before retry due to", error_summary)
    print()
    sleep(100)
    print()
    print("retrying on", datetime.now().strftime("%H:%M:%S (%Y-%m-%d)"))

def create_table_if_needed(cursor):
    if "history_api_cache" in existing_tables(cursor):
        pass
        #print("history_api_cache table exists already, delete file with database to recreate")
    else:
        # for_changeset_id
        # this exists because for future changesets new history may be present and will need to be refetched
        cursor.execute('''CREATE TABLE history_api_cache
                    (for_changeset_id integer, object_type text, object_id integer, serialized_history text)''')

        # magnificent speedup
        # TODO make indexes as needed
        #cursor.execute("""CREATE INDEX idx_osm_data_area_identifier ON osm_data (area_identifier);""")
        #cursor.execute("""CREATE INDEX idx_osm_data_id_type ON osm_data (id, type);""")
    if "changeset_object_api_cache" in existing_tables(cursor):
        pass
        #print("changeset_object_api_cache table exists already, delete file with database to recreate")
    else:
        cursor.execute('''CREATE TABLE changeset_object_api_cache
                    (changeset_id integer, element_list text)''')

    if "changeset_metadata_api_cache" in existing_tables(cursor):
        pass
        #print("changeset_metadata_api_cache table exists already, delete file with database to recreate")
    else:
        cursor.execute('''CREATE TABLE changeset_metadata_api_cache
                    (changeset_id integer, serialized text)''')

def existing_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_listing = cursor.fetchall()
    returned = []
    for entry in table_listing:
        returned.append(entry[0])
    return returned

def check_database_integrity(cursor):
    cursor.execute("PRAGMA integrity_check;")
    info = cursor.fetchall()
    if (info != [('ok',)]):
        raise

def database_filepath():
    return '/media/mateusz/OSM_cache/cache-for-osm-editing-api/database.db'

def is_one_of_shop_associated_keyes_removed_on_replacement(key):
    for regex in KEYS_THAT_SHOULD_BE_REMOVED_WHEN_SHOP_IS_REPLACED_REGEXES():
        if re.match('\A' + regex + '\Z', key):
            #print(regex, "matched", key)
            return True
    return False


# // generated by "make update" from https://github.com/mnalis/StreetComplete-taginfo-categorize/
# val KEYS_THAT_SHOULD_BE_REMOVED_WHEN_SHOP_IS_REPLACED = listOf(
def KEYS_THAT_SHOULD_BE_REMOVED_WHEN_SHOP_IS_REPLACED_REGEXES():
    return [
    "shop_?[1-9]?(:.*)?", "craft_?[1-9]?", "amenity_?[1-9]?", "old_amenity", "old_shop",
    "information", "leisure", "office_?[1-9]?", "tourism",
    # popular shop=* / craft=* subkeys
    "marketplace", "household", "swimming_pool", "laundry", "golf", "sports", "ice_cream",
    "scooter", "music", "retail", "yes", "ticket", "newsagent", "lighting", "truck", "car_repair",
    "car_parts", "video", "fuel", "farm", "car", "tractor", "hgv", "ski", "sculptor",
    "hearing_aids", "surf", "photo", "boat", "gas", "kitchen", "anime", "builder", "hairdresser",
    "security", "bakery", "bakehouse", "fishing", "doors", "kiosk", "market", "bathroom", "lamps",
    "vacant", "insurance(:.*)?", "caravan", "gift", "bicycle", "bicycle_rental", "insulation",
    "communication", "mall", "model", "empty", "wood", "hunting", "motorcycle", "trailer",
    "camera", "water", "fireplace", "outdoor", "blacksmith",
    # obsoleted information
    "abandoned(:.*)?", "disused(:.*)?", "was:.*", "not:.*", "damage", "source:damage",
    "created_by", "check_date", "opening_date", "last_checked", "checked_exists:date",
    "pharmacy_survey", "old_ref", "update", "import_uuid",
    # classifications / links to external databases
    "fhrs:.*", "old_fhrs:.*", "fvst:.*", "ncat", "nat_ref", "gnis:.*", "winkelnummer",
    "type:FR:FINESS", "type:FR:APE", "kvl_hro:amenity", "ref:DK:cvr(:.*)?", "certifications?",
    "transiscope", "opendata:type",
    # names and identifications
    "name_?[1-9]?(:.*)?", ".*_name_?[1-9]?(:.*)?", "noname", "branch(:.*)?", "brand(:.*)?",
    "not:brand(:.*)?", "network", "operator(:.*)?", "operator_type", "ref", "ref:vatin",
    "designation", "SEP:CLAVEESC", "identifier",
    # contacts
    "contact_person", "contact(:.*)?", "phone(:.*)?", "phone_?[1-9]?", "emergency:phone", "mobile",
    "fax", "facebook", "instagram", "twitter", "youtube", "telegram", "email",
    "website_?[1-9]?(:.*)?", "app:.*", "ownership",
    "url", "source_ref:url", "owner",
    # payments
    "payment(:.*)?", "payment_multi_fee", "currency:.*", "cash_withdrawal(:.*)?", "fee", "charge",
    "charge_fee", "money_transfer", "donation:compensation",
    # generic shop/craft attributes
    "seasonal", "time", "opening_hours(:.*)?", "check_date:opening_hours", "wifi", "internet",
    "internet_access(:.*)?", "second_hand", "self_service", "automated", "license:.*",
    "bulk_purchase", ".*:covid19", "language:.*", "baby_feeding", "description(:.*)?",
    "description[0-9]", "min_age", "max_age", "supermarket(:.*)?", "social_facility(:.*)?",
    "functional", "trade", "wholesale", "sale", "smoking", "zero_waste", "origin", "attraction",
    "strapline", "dog", "showroom", "toilets?(:.*)?", "changing_table", "wheelchair(.*)?", "blind",
    "company(:.*)?", "stroller", "walk-in", "webshop", "operational_status.*", "drive_through",
    "surveillance(:.*)?", "outdoor_seating", "indoor_seating", "colour", "access_simple", "floor",
    "product_category", "source_url", "category", "kids_area", "resort", "since", "state",
    "operational_status", "temporary",
    # food and drink details
    "bar", "cafe", "coffee", "microroasting", "microbrewery", "brewery", "real_ale", "taproom",
    "training", "distillery", "drink(:.*)?", "cocktails", "alcohol", "wine([:_].*)?",
    "happy_hours", "diet:.*", "cuisine", "tasting", "breakfast", "lunch", "organic",
    "produced_on_site", "restaurant", "food", "pastry", "pastry_shop", "product", "produce",
    "chocolate", "fair_trade", "butcher", "reservation(:.*)?", "takeaway(:.*)?", "delivery(:.*)?",
    "caterer", "real_fire", "flour_fortified", "highchair", "sport_pub",
    # related to repair shops/crafts
    "service(:.*)?", "motorcycle:.*", "repair", ".*:repair", "electronics_repair(:.*)?",
    "workshop",
    # shop=hairdresser, shop=clothes
    "unisex", "male", "female", "gender", "lgbtq(:.*)?",
    # healthcare
    "healthcare(:.*)?", "health", "health_.*", "medical_.*", "facility(:.*)?", "activities",
    "healthcare_facility(:.*)?", "laboratory(:.*)?", "blood(:.*)?", "blood_components",
    "infection(:.*)?", "disease(:.*)?", "covid19(:.*)?", "CovidVaccineCenterId",
    "coronaquarantine", "hospital(:.*)?", "hospital_type_id", "emergency_room",
    "sample_collection(:.*)?", "bed_count", "capacity:beds", "part_time_beds", "personnel:count",
    "staff_count(:.*)?", "admin_staff", "doctors_num", "nurses_num", "counselling_type",
    "testing_centres", "toilets_number", "urgent_care", "vaccination", "clinic", "hospital",
    "pharmacy", "laboratory", "sample_collection", "provided_for(:.*)?", "social_facility_for",
    "ambulance", "ward", "HSE_(code|hgid|hgroup|region)", "collection_centre", "design",
    "AUTORIZATIE", "reg_id", "scope", "ESTADO", "NIVSOCIO", "NO", "EMP_EST", "COD_HAB", "CLA_PERS",
    "CLA_PRES", "snis_code:.*", "hfac_bed", "hfac_type", "nature", "moph_code", "IJSN:.*",
    "massgis:id", "OGD-Stmk:.*", "paho:.*", "panchayath", "pbf_contract", "pcode", "pe:minsa:.*",
    "who:.*",
    # accommodation & layout
    "rooms", "stars", "accommodation", "beds", "capacity(:persons)?", "laundry_service",
    # misc specific attributes
    "clothes", "shoes", "tailor", "beauty", "tobacco", "carpenter", "furniture", "lottery",
    "sport", "leisure", "dispensing", "tailor:.*", "gambling", "material", "raw_material",
    "stonemason", "studio", "scuba_diving(:.*)?", "polling_station", "club", "collector", "books",
    "agrarian", "musical_instrument", "massage", "parts", "post_office(:.*)?", "religion",
    "denomination", "rental", ".*:rental", "tickets:.*", "public_transport", "goods_supply", "pet",
    "appliance", "artwork_type", "charity", "company", "crop", "dry_cleaning", "factory",
    "feature", "air_conditioning", "atm", "vending", "vending_machine", "recycling_type", "museum",
    "license_classes", "dance:style", "isced:level", "school", "preschool", "university",
    "research_institution", "research", "member_of", "topic", "townhall:type", "parish", "police",
    "government", "office", "administration", "administrative", "association", "transport",
    "utility", "consulting", "commercial", "private", "taxi", "admin_level", "official_status",
    "target", "liaison", "diplomatic(:.*)?", "embassy", "consulate", "aeroway", "department",
    "faculty", "aerospace:product", "boundary", "population", "diocese", "depot", "cargo",
    "function", "game", "party", "telecom(munication)?", "service_times", "kitchen:facilities",
    "it:(type|sales)", "cannabis:cbd",
    "camp_site", "camping", "emergency(:.*)?", "evacuation_cent(er|re)", "education",
    "engineering", "forestry", "foundation", "lawyer", "logistics", "military", "community_centre",
    "bank",
    ]

main()

