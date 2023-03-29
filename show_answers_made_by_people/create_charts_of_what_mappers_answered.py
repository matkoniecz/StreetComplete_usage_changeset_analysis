import matplotlib.pyplot as plt
import numpy as np
import sys
import collections
import functools
import csv

def main():
    show_data_for_quest("CheckExistence")
    show_data_for_quest("AddOpeningHours")
    show_data_for_quest("AddFireHydrantDiameter")

def show_data_for_quest(quest):
    plt.rcParams["figure.figsize"] = [20, 10]
    # see https://github.com/matkoniecz/quick-beautiful/tree/master/10-nice-graphs for my research on styling
    plt.style.use('fivethirtyeight')
    plt.grid(True)

    with open('/media/mateusz/OSM_cache/cache-for-osm-editing-api/some.csv') as csvfile:
        reader = csv.reader(csvfile)
        #headers = next(reader, None)

        oldest = 0
        sorted_by_main_tag = {}
        for row in reader:
            print(row)
            quest_type = row[0]
            outcome = row[1]
            days = int(row[2])
            main_tag = row[3]
            link = row[4]
            if quest_type != quest:
                continue
            if outcome == '????TODO':
                print("unhandled", row)
                continue
            if main_tag not in sorted_by_main_tag:
                sorted_by_main_tag[main_tag] = []
            sorted_by_main_tag[main_tag].append({'outcome': outcome, 'days': days, 'main_tag': main_tag, 'link': link})
            if oldest < days:
                oldest = days
        for key in sorted_by_main_tag.keys():
            print(key, len(sorted_by_main_tag[key]))
        print(oldest)
        bin_size = 365
        bin_count = oldest // bin_size + 1

        labels = [str(i) + " - " + str(i + 1) for i in range(bin_count)]
        print(labels)

        for main_tag in sorted_by_main_tag.keys():
            bins = []
            for _ in range(bin_count):
                bins.append({'acted': 0, 'marked_as_surveyed': 0, 'ratio': np.nan})
            for entry in sorted_by_main_tag[main_tag]:
                if "node" not in entry["link"]:
                    # https://www.openstreetmap.org/way/310581611/history
                    continue
                bin_index = entry['days'] // bin_size
                if entry['outcome'] == 'marked_as_surveyed':
                    bins[bin_index]['marked_as_surveyed'] += 1
                if entry['outcome'] == 'deleted' or entry['outcome'] == 'changed_data_tags':
                    bins[bin_index]['acted'] += 1
                bins[bin_index]['ratio'] = bins[bin_index]['marked_as_surveyed'] / (bins[bin_index]['marked_as_surveyed'] + bins[bin_index]['acted'])
            #print(bins)
            data = []
            has_real_data = False
            total_marked_as_surveyed = 0
            total_acted = 0
            for bin_index in range(bin_count):
                marked_as_surveyed = bins[bin_index]['marked_as_surveyed']
                total_marked_as_surveyed += marked_as_surveyed
                acted = bins[bin_index]['acted']
                total_acted += acted
                #print()
                #print(marked_as_surveyed)
                #print(acted)
                #print(bins[bin_index]['ratio'])
                ratio = bins[bin_index]['ratio']
                if (marked_as_surveyed + acted) < 100:
                    ratio = np.nan
                else:
                    has_real_data = True
                data.append(ratio)

            sample = total_marked_as_surveyed + total_acted
            ratio = total_marked_as_surveyed / sample
            if has_real_data or (ratio > 0.99 and total_marked_as_surveyed > 100):
                objects = labels
                y_pos = np.arange(len(objects))
                plt.clf()
                plt.bar(y_pos, data, align='center', alpha=0.5)
                plt.xticks(y_pos, objects)
                plt.ylabel('Value')
                title = main_tag + " " + str(int(ratio*100)) + "." + str(int(ratio*1000)%10) + "% got only check data changed, sample " + str(sample)
                print(title)
                plt.title(title)
                plt.savefig(main_tag + '.png')
                #plt.show()


main()