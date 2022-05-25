import sys
import subprocess
import os
import natsort

# p collect_info_about_quests_disabled_by_version.py "/home/mateusz/Documents/install_moje/OSM software/StreetComplete"

def main():
    write_to = os.getcwd()
    sc_folder_location = sys.argv[1]
    os.chdir(sc_folder_location)
    versions = get_stdout_lines_from_command("git tag -l v*".split(" "))
    print(versions)
    versions = natsort.natsorted(versions)
    yaml = ""
    print(versions)
    yaml += "{\n"
    for version in versions:
        print()
        if "mnalis" in version:
            continue
        print("version", version)
        get_stdout_lines_from_command(['git', 'checkout', version, "-f"])
        filepaths_with_mention_of_parameter_disabling_quests = sorted(get_stdout_lines_from_command(["rg", "-l", "defaultDisabledMessage"]))
        quests_disabled = []
        for line in filepaths_with_mention_of_parameter_disabling_quests:
            filename = line.split("/")[-1]
            quest = filename.split(".")[0]
            if filename.split(".")[1] != "kt":
                continue # mentioned for example in CONTRIBUTING_A_NEW_QUEST.MD
            if quest in ["TestQuestType", "QuestType", "DisabledTestQuestType",
            "VisibleQuestTypeController", "QuestSelectionAdapter",
            "VisibleQuestTypeDao", "TestQuestTypes"]:
                continue
            quests_disabled.append(quest)
        if len(quests_disabled) < 3:
            yaml += "  '" + version + "': [" + "'" + "', '".join(quests_disabled) + "'" + "],\n"
        else:
            yaml += "  '" + version + "': [\n" + "    '" + "',\n    '".join(quests_disabled) + "',\n" + "  ],\n"
    yaml += "}\n"
    os.chdir(write_to)
    with open("disabled_quests.yaml", 'w') as outfile:
        outfile.write(yaml)

#https://www.openstreetmap.org/user/wielandb/diary/399164#comment52478


def get_stdout_lines_from_command(command):
    #print(command)
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    output = output.decode('utf-8').strip()
    error = error.decode('utf-8').strip()
    #print()
    #print("output")
    #print(output)
    #print("error")
    #print(error)
    #print()
    if output == "":
        return []
    return output.split("\n")

main()