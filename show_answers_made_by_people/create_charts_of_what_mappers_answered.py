import matplotlib.pyplot as plt
import numpy as np
import sys
import collections
import functools
import csv

def main():
    plt.rcParams["figure.figsize"] = [10, 10]
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
            outcome = row[0]
            days = int(row[1])
            main_tag = row[2]
            link = row[3]
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

        for tag in sorted_by_main_tag.keys():
            bins = []
            for _ in range(bin_count):
                bins.append({'deleted': 0, 'marked_as_surveyed': 0, 'ratio': np.nan})
            for entry in sorted_by_main_tag[main_tag]:
                bin_index = entry['days'] // bin_size
                if entry['outcome'] == 'marked_as_surveyed':
                    bins[bin_index]['marked_as_surveyed'] += 1
                if entry['outcome'] == 'deleted':
                    bins[bin_index]['deleted'] += 1
                bins[bin_index]['ratio'] = bins[bin_index]['marked_as_surveyed'] / (bins[bin_index]['marked_as_surveyed'] + bins[bin_index]['deleted'])
            print(bins)
            data = []
            for i in range(bin_count):
                data.append(bins[i]['ratio'])
            
            objects = labels
            y_pos = np.arange(len(objects))
            performance = [6, 4, 2, np.nan, 1]
            plt.clf()
            plt.bar(y_pos, data, align='center', alpha=0.5)
            plt.xticks(y_pos, objects)
            plt.ylabel('Value')
            plt.title(tag)
            plt.savefig('bargraph.png')
            plt.show()


main()