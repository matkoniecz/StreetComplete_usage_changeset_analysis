from osm_easy_api import Api
import csv
import sqlite3
import json
from osm_easy_api.data_classes import Node, Way, Relation, Changeset, OsmChange, Action, Tags

from osm_easy_api.diff import diff_parser
from datetime import datetime
from osm_bot_abstraction_layer import utils
import time
import osm_bot_abstraction_layer.tag_knowledge as tag_knowledge

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

def selftest(cursor):
    api = Api(url='https://openstreetmap.org')
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
    analyse_history(cursor, api, '118933758', 'CheckExistence')

def specific_test_cases(cursor):
    deleting_points = 133235020
    deleting_areas = 133234704
    tag_edit = 133266712
    # https://www.openstreetmap.org/changeset/133522260
    splitting_ways_and_adding_tags = 133522260
    deletion_undone_in_the_separate_changeset = 126057446

    api = Api(url='https://openstreetmap.org')

    analyse_history(cursor, api, deletion_undone_in_the_separate_changeset, 'CheckExistence')

def main():
    connection = sqlite3.connect(database_filepath())
    cursor = connection.cursor()
    create_table_if_needed(cursor)
    check_database_integrity(cursor)
    selftest(cursor)
    specific_test_cases(cursor)

    api = Api(url='https://openstreetmap.org')

    stats = []
    todocount = 0
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
                stats += analyse_history(cursor, api, edit_id, quest_type)
            if quest_type == "AddOpeningHours":
                stats += analyse_history(cursor, api, edit_id, quest_type)
            if quest_type == "AddFireHydrantDiameter":
                stats += analyse_history(cursor, api, edit_id, quest_type)
            connection.commit()
    #print(json.dumps(stats, default=str, indent=3))
    with open('/media/mateusz/OSM_cache/cache-for-osm-editing-api/some.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        for entry in stats:
            if entry['action'] == '????TODO':
                todocount += 1
            else:
                if 'days' in entry:
                    writer.writerow([entry["quest_type"], entry["action"], entry["days"], entry["main_tag"], entry["link"]])
                else:
                    print(entry)
    connection.close()
    print(todocount, 'unhandled entries')

def get_main_key_from_tags(tags):
    for potential_main_key in tag_knowledge.typical_main_keys():
        if potential_main_key in tags:
            return potential_main_key + " = " + tags[potential_main_key]
    #return "wat=wat" # TODO investigate
    # {'addr:city': 'Siegen', 'addr:country': 'DE', 'addr:housenumber': '16', 'addr:postcode': '57076', 'addr:street': 'Wilhelm-von-Humboldt-Platz', 'email': 'info@service-transport.de', 'mobile': '+49 152 51427455', 'name': 'S-Transport Haushaltsauflösungen & Entrümpelungen in Siegen', 'opening_hours': 'Mo-Fr 08:00-20:00, Sa 08:00-18:00', 'phone': '+49 271 23571842', 'website': 'https://www.service-transport.de'}
    print("main tag - failed to find for ", tags)
    return None

def analyse_history(local_database_cursor, api, changeset_id, quest_type):
    new_stats = []
    for element in elements_edited_by_changeset(local_database_cursor, api, changeset_id):
        history = object_history(local_database_cursor, api, changeset_id, element)
        link = "https://www.openstreetmap.org/" + type(element).__name__.lower() + "/" + str(element.id) + "/history"
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
                            new_stats.append({"quest_type": quest_type, "action": '????TODO', 'main_tag': None, 'link': link})
                            # TODO: handling do-revert-do_something_else (right now all three would be treated as reverts)
                            return new_stats
                        if entry.user_id == potential_duplicate_entry.user_id:
                            print(changeset_metadata(local_database_cursor, api, entry.changeset_id))
                            print(changeset_metadata(local_database_cursor, api, potential_duplicate_entry.changeset_id))
                            # smarter checks: blocked by https://github.com/docentYT/osm_easy_api/issues/7 for now
                            new_stats.append({"quest_type": quest_type, "action": '????TODO - the same user, assuming the same action', 'main_tag': None, 'link': link})
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
                            affected = affected_tags(entry, previous_entry)
                            
                            tags_that_could_be_just_removed_in_addition = [
                                # LAST_CHECK_DATE_KEYS
                                #"check_date", - used by SC
                                "lastcheck",
                                "last_checked",
                                "survey:date",
                                "survey_date",
                            ]
                            for tag in tags_that_could_be_just_removed_in_addition:
                                if tag in affected:
                                    affected.remove(tag)
                            if affected == ["check_date:opening_hours"] or affected == ["check_date"] or affected == ["opening_hours:signed"] or affected == ['fire_hydrant:diameter:signed']:
                                #print("MARKED AS STILL EXISTING")
                                new_stats.append({"quest_type": quest_type, "action": 'marked_as_surveyed', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif affected == ['traffic_calming']:
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif affected == ['fire_hydrant:diameter']:
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif affected == ["opening_hours"] or affected == ['check_date:opening_hours', 'opening_hours'] or affected == ['check_date:opening_hours', 'opening_hours', 'opening_hours:signed']:
                                #print("COLLECTED NEW DATA")
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif affected == ['disused:shop', 'name', 'shop']:
                                # shop is gone
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})
                            elif "disused:shop" in affected:
                                # flipped shop type, probably
                                new_stats.append({"quest_type": quest_type, "action": 'changed_data_tags', 'days': days, 'main_tag': main_tag, 'link': link})
                            else:
                                print(link)
                                print("NOT HANDLED")
                                print(affected)
                                print()
                #print("==============")
                #print()
    return new_stats

def affected_tags(entry, previous_entry):
    #print(previous_entry.tags)
    #print(entry.tags)
    affected = []
    for key in entry.tags.keys():
        if key in previous_entry.tags.keys():
            if entry.tags[key] == previous_entry.tags[key]:
                pass
            else:
                #print("MODIFIED", key, "=", entry.tags[key], "to", key, "=", previous_entry.tags[key])
                affected.append(key)
        else:
            #print("ADDED", key, "=", entry.tags[key])
            affected.append(key)
    for key in previous_entry.tags.keys():
        if key in entry.tags:
            pass
        else:
            #print("REMOVED", key, "=", previous_entry.tags[key])
            affected.append(key)
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

    print("MAKING A CALL TO OSM API - api.changeset.download(", changeset_id, ")")
    downloaded = api.changeset.get(changeset_id)

    serialized = json.dumps(downloaded.to_dict(), default=str, indent=3)
    local_database_cursor.execute("INSERT INTO changeset_metadata_api_cache VALUES (:changeset_id, :serialized)", {"changeset_id": changeset_id, 'serialized': serialized})
    return serialized

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

    if "changeset_metadata_api_cache" in existing_tables(cursor):
        print("changeset_metadata_api_cache table exists already, delete file with database to recreate")
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

main()
