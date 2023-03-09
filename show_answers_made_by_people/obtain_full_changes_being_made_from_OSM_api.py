from osm_easy_api import Api
import csv
import sqlite3
import json
from osm_easy_api.data_classes import Node, Way, Relation, OsmChange, Action, Tags

from osm_easy_api.diff import diff_parser
from datetime import datetime
from osm_bot_abstraction_layer import utils
import time

# https://github.com/docentYT/osm_easy_api
"""

python3.10 obtain_full_changes_being_made_from _OSM_api.py

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

def selftest():
    api = Api(url='https://openstreetmap.org')
    node = api.elements.get(Node, 25733488)
    dict = node.to_dict()
    node_from_dict = Node.from_dict(dict)
    print(dict)

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
    print(node)


def main():
    selftest()
    connection = sqlite3.connect(database_filepath())
    cursor = connection.cursor()
    create_table_if_needed(cursor)
    check_database_integrity(cursor)

    api = Api(url='https://openstreetmap.org')

    stats = []
    with open('/media/mateusz/OSM_cache/changesets/sc_edits_list_from_2021-05-20_to_2023-02-20.csv') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader, None)
        for row in reader:
            edit_id = int(row[0])
            if edit_id < 117645886:
                continue
            editor = row[1]
            quest_type = row[3]
            if quest_type == "CheckExistence":
                stats = analyse_history(cursor, api, edit_id, stats, quest_type)
            if quest_type == "AddFireHydrantDiameter":
                print(quest_type)
            connection.commit()
    print(json.dumps(stats, default=str, indent=3))
    with open('/media/mateusz/OSM_cache/cache-for-osm-editing-api/some.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        for entry in stats:
            writer.writerow([entry["quest_type"], entry["action"], entry["days"], entry["main_tag"], entry["link"]])
    deleting_points = 133235020
    deleting_areas = 133234704
    tag_edit = 133266712
    connection.close()

def get_main_key_from_tags(tags):
    for potential_main_key in ["amenity", "shop", "barrier", "leisure", "advertising", "emergency",
    "tourism", "man_made", "traffic_calming"]: # TODO - synchronize it with that NSI parser, upwell into osm_bot_abstraction_layer
        if potential_main_key in tags:
            return potential_main_key + " = " + tags[potential_main_key]
    raise Exception("main tag - failed to find for ", tags)

def analyse_history(local_database_cursor, api, changeset_id, stats, quest_type):
    for element in elements_edited_by_changeset(local_database_cursor, api, changeset_id):
        history = object_history(local_database_cursor, api, changeset_id, element)
        link = "https://www.openstreetmap.org/" + type(element).__name__.lower() + "/" + str(element.id) + "/history"
        print(link)
        edited_count = 0
        for index, entry in enumerate(history):
            if entry.changeset_id == changeset_id:
                if index == 0:
                    print("StreetComplete created an object")
                else:
                    previous_entry = history[index - 1]
                    this_timestamp = datetime.strptime(entry.timestamp, utils.typical_osm_timestamp_format())
                    previous_timestamp = datetime.strptime(previous_entry.timestamp, utils.typical_osm_timestamp_format())
                    days = (this_timestamp - previous_timestamp).days
                    print(days, "days")
                    print(previous_entry.tags)
                    print(entry)
                    main_tag = get_main_key_from_tags(previous_entry.tags)
                    if entry.visible == False:
                        stats.append({"quest_type": quest_type, "action": 'deleted', 'days': days, 'main_tag': main_tag, 'link': link})
                        print("DELETED")
                    else:
                        print("MARKED AS STILL EXISTING")
                        stats.append({"quest_type": quest_type, "action": 'marked_as_surveyed', 'days': days, 'main_tag': main_tag, 'link': link})
                    edited_count += 1
                print("==============")
                print()
        if edited_count > 1:
            print("multiple edits - reverts?")
    return stats

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
    for action in changeset_data(local_database_cursor, api, changeset_id):
        element = action[1]
        element_list.append(element)
    saved_as_json = serialize_element_list(element_list)
    local_database_cursor.execute("INSERT INTO changeset_object_api_cache VALUES (:changeset_id, :element_list)", {"changeset_id": changeset_id, 'element_list': saved_as_json})

    return element_list


def changeset_data(local_database_cursor, api, changeset_id):
    print("MAKING A CALL TO OSM API - api.changeset.download(", changeset_id, ")")
    downloaded = api.changeset.download(changeset_id)
    for action in downloaded:
        if action[0] != Action.MODIFY and action[0] != Action.DELETE and action[0] != Action.CREATE:
            print(action)
            raise
        print(action)
        yield action
    # multiple entries
    # changeset_id, action, object_type

def object_history(local_database_cursor, api, for_changeset_id, element_as_osm_easy_api_object):
    element_type_label = type(element_as_osm_easy_api_object).__name__.lower()
    print(element_type_label)
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

    local_database_cursor.execute("INSERT INTO history_api_cache VALUES (:for_changeset_id, :object_type, :object_id, :serialized_history)", {"for_changeset_id": for_changeset_id, 'object_type': element_type_label, 'object_id': element_as_osm_easy_api_object.id, 'serialized_history': serialized})

    return returned

def prepare_history_api_call_function(api, element_as_osm_easy_api_object):
    def execute_api_call():
        print("MAKING A CALL TO OSM API - api.elements.history(", element_as_osm_easy_api_object.__class__, ",",  element_as_osm_easy_api_object.id, ")")
        print(element_as_osm_easy_api_object.__class__, element_as_osm_easy_api_object.id)
        return api.elements.history(element_as_osm_easy_api_object.__class__, element_as_osm_easy_api_object.id)
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
        print("history_api_cache table exists already, delete file with database to recreate")
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
        print("changeset_object_api_cache table exists already, delete file with database to recreate")
    else:
        cursor.execute('''CREATE TABLE changeset_object_api_cache
                    (changeset_id integer, element_list text)''')

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

main()
