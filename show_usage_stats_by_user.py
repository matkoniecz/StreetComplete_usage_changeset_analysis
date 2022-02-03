#import requests
import sys
import os
import random
import datetime
import time
from PIL import Image

def get_file_location():
    # changeset data can be obtained with https://github.com/matkoniecz/StreetComplete_usage_changeset_analysis#streetcomplete_edits_generate_csv_and_make_quest_summaryphp

    file_location = "/media/mateusz/OSM_cache/edits_with_all_declared_software.csv"
    #file_location = "/media/mateusz/OSM_cache/reduced.csv"
    if len(sys.argv) != 2:
        print("call it with a single arguments specifying location of a csv file")
        print("csv file must be made in format changeset_id,created_by,2018-03-18T11:58:10Z,ANY_FIELD,user_id")
        print("2018-03-18T11:58:10Z above is date format example")
        print("(for example by https://github.com/matkoniecz/StreetComplete_usage_changeset_analysis#streetcomplete_edits_generate_csv_and_make_quest_summaryphp )")

        print()
        print("defaulting to", file_location)
    else:
        file_location = sys.argv[1]
    return file_location

def user_list(file_location):
    start = time.time()
    users = set()
    sc_users = set()
    # changeset_id,created_by,creation_date,changed_objects,user_id
    with open(file_location) as fp:
        next(fp) # skip header
        for line in fp:
            line = line.split(",")
            changeset_id = int(line[0])
            user_id = int(line[-1])
            if user_id not in users:
                users.add(user_id)
            editor = line[1]
            sc_edit = "StreetComplete" in editor or "Zażółć" in editor or "Zazolc" in editor
            if sc_edit and user_id not in sc_users:
                sc_users.add(user_id)
    return {'users': users, 'sc_users': sc_users}

def main():
    start = time.time()
    file_location = get_file_location()
    user_data = user_list(file_location)
    users = user_data['users']
    sc_users = user_data['sc_users']

    print(len(users), "mappers,", len(sc_users), "SC mappers")

    users_who_made_an_edit = []

    # each pixel is one day of one user
    #gray: days before the first edit (registration?)
    #black: after initial
    #blue: days with edit, without StreetComplete edits
    #yellow: days with edit, only StreetComplete
    #green: days with edit, both SC and regular

    # note: https://en.wikipedia.org/wiki/Reservoir_sampling may be more elegant, with a single pass


    # around 39k users with at least one SC edit
    # around 17 420k users with at least one edit

    #1920*2 x 1200 = 10.5 roku

    print("pregeneration done in", int(time.time() - start), "seconds")

    for i in range(20):
        generate_image(file_location, str(i+1), random.sample(users, len(sc_users)), sc_users)
    #users = [1722488] + random.sample(users, 1200-1)
    #sc_users = [1722488] + random.sample(sc_users, 1200-1)
    #day_range = 1200*2 # to fit my screen

def date_range(file_location):
    first_day = None
    last_day = None
    with open(file_location) as fp:
        next(fp) # skip header
        line = next(fp)
        first_day = date_from_split_changeset_line(line.split(","))
        for line in fp:
            pass
        last_line = line
        last_day = date_from_split_changeset_line(last_line.split(",")) - datetime.timedelta(days=1)
    return first_day, last_day

def generate_image(file_location, suffix, users, sc_users):
    first_day, last_day = date_range(file_location)
    print(first_day, last_day)
    day_count = (last_day - first_day).days + 1
    start = time.time()

    nonsc_edit_per_user = {}
    sc_edit_per_user = {}
    for user in users:
        nonsc_edit_per_user[user] = [0] * day_count
        sc_edit_per_user[user] = [0] * day_count
    day_of_the_first_edit_of_user = {}

    nonsc_edit_per_sc_user = {}
    sc_edit_per_sc_user = {}
    for user in sc_users:
        nonsc_edit_per_sc_user[user] = [0] * day_count
        sc_edit_per_sc_user[user] = [0] * day_count
    day_of_the_first_edit_of_sc_user = {}

    today = datetime.datetime.now()

    skip_changeset_with_id_lower_than = 1 # allows quick restart of script after processing part of data
    # changeset_id,created_by,creation_date,changed_objects,user_id
    index = 0
    with open(file_location) as fp:
        next(fp) # skip header
        for line in fp:
            index += 1
            if index % 1_000_000 == 0:
                print("processed", str(index/1_000_000) + "M edits in", int(time.time() - start), "seconds")
            line = line.split(",")
            user_id = int(line[-1])
            if user_id not in users and user_id not in sc_users:
                continue

            editor = line[1]
            sc_edit = "StreetComplete" in editor or "Zażółć" in editor or "Zazolc" in editor
            date_object = date_from_split_changeset_line(line)
            days_since_initial = (date_object - first_day).days

            if user_id in users:
                if user_id not in day_of_the_first_edit_of_user:
                    day_of_the_first_edit_of_user[user_id] = days_since_initial
            if user_id in sc_users:
                if user_id not in day_of_the_first_edit_of_sc_user:
                    day_of_the_first_edit_of_sc_user[user_id] = days_since_initial
            
            if date_object < first_day:
                continue
            if date_object > last_day:
                continue
            if user_id in users:
                if sc_edit:
                    sc_edit_per_user[user_id][days_since_initial] += 1
                else:
                    nonsc_edit_per_user[user_id][days_since_initial] += 1
            if user_id in sc_users:
                if sc_edit:
                    sc_edit_per_sc_user[user_id][days_since_initial] += 1
                else:
                    nonsc_edit_per_sc_user[user_id][days_since_initial] += 1
    print("specific pair data collection done in", int(time.time() - start), "seconds")
    start = time.time()
    generate_specific_image(sc_edit_per_user, nonsc_edit_per_user, day_of_the_first_edit_of_user, "regular_users_" + suffix + ".png")
    generate_specific_image(sc_edit_per_sc_user, nonsc_edit_per_sc_user, day_of_the_first_edit_of_sc_user, "sc_users_" + suffix + ".png")
    print("specific pair image drawing done in", int(time.time() - start), "seconds")

def date_from_split_changeset_line(line):
    time_string = line[2]
    try:
        return datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%SZ").date()
    except ValueError as e:
        print(line)
        print(time_string)
        raise e

def generate_specific_image(sc_edits, nonsc_edits, day_of_the_first_edit, filename):
    example_user = next(iter(sc_edits.keys()))
    days = len(sc_edits[example_user])

    # TODO: order users by the first edit
    # TODO: make space before the first edit gray


    width = days
    height = len(sc_edits)
    im = Image.new("RGB", (width, height), (0, 0, 0))
    pixels = im.load()
    user_index = 0
    for user, day_of_the_first_edit in sorted(day_of_the_first_edit.items(), key=lambda x: [1]):
        for i in range(days):
            if sc_edits[user][i] and not nonsc_edits[user][i]:
                pixels[i, user_index] = (20, 255, 20)
            elif sc_edits[user][i] and nonsc_edits[user][i]:
                pixels[i, user_index] = (255, 255, 255)
            elif not sc_edits[user][i] and nonsc_edits[user][i]:
                pixels[i, user_index] = (20, 20, 255)
            elif i < day_of_the_first_edit:
                pixels[i, user_index] = (30, 30, 30)
        user_index += 1
    im.save(filename)
    print(filename, "saved")
    #im.show()

main()
