<?php
// special thanks to @Zverik for answering https://github.com/Zverik/editor-stats/issues/4 
// without this I would not expect processing such data to be feasible (changeset planet file can be read line by line)!


// for assumptions being made about file format, allowing to process it without
// parsing it as an XML, see extracting_data_from_xml_line.php file

require_once('extracting_data_from_xml_line.php');

function main($filename) {
    $file = new SplFileObject($filename);

    $outputFile = fopen("output.csv", "w") or die("Unable to open file!");
    fwrite($outputFile, "changeset_id" . "," . "editor" . "," . "changed_objects" . "," . "quest_type" . "," . "user_id" . "\n");

    $popularity = array();
    // based on https://stackoverflow.com/questions/13246597/how-to-read-a-large-file-line-by-line
    // Loop until we reach the end of the file.
    while (!$file->eof()) {
        $line = trim($file->fgets());
        if ($line == "</changeset>") {
            #echo $line;
            #echo "end of a changeset with tags\n\n";
            $changeset_header = NULL;
        } elseif (str_begins($line, "<changeset")) {
            if(str_ends($line, '">')) {
                #echo $line;
                $changeset_header = $line;
                #echo "new changeset, with tags\n\n";
            } else {
                #echo $line;
                #echo "new changeset, without tags\n\n";
            }
        } else {
            if(str_begins($line, '<tag k="created_by"')) {
                if(contains_substr($line, "StreetComplete") || contains_substr($line, "zażółć")) {
                    #echo $changeset_header;
                    #echo "\n";
                    #echo $line;
                    #echo "\n";
                    #echo "created by tag\n";
                }
            } elseif (str_begins($line, '<tag k="StreetComplete:quest_type"') || str_begins($line, '<tag k="zażółć:quest_type"')) {
                #echo $line;
                #echo "\n";
                #echo "quest type tag";
                #echo get_changes_number($changeset_header);
                #echo "\n";
                if(str_begins($line, '<tag k="StreetComplete:quest_type"')){
                    $editor = "StreetComplete";
                } elseif(str_begins($line, '<tag k="zażółć:quest_type"')){
                    $editor = "StreetComplete";
                } else {
                    $editor = "?";
                }
                $id = get_changeset_id($changeset_header);
                $count = get_changes_number($changeset_header);
                $type = get_quest_type($line);
                $uid = get_uid($changeset_header);
                fwrite($outputFile, $id . "," . $editor . "," . $count . "," . $type . "," . $uid . "\n");
                $popularity = register_popularity($popularity, $type, get_changes_number($changeset_header));
                #var_dump($popularity);
                #echo "\n\n";
            }
        }
    }

    arsort($popularity);
    foreach ($popularity as $quest_identifier => $total_edits) {
        echo "$quest_identifier : $total_edits\n";
    }

    echo("\n");
    echo("\n");
    echo("\n");
    echo "| QuestCode        | Total modified elements           |\n";
    echo "| ------------- |-------------|\n";
    foreach ($popularity as $quest_identifier => $total_edits) {
        echo "| $quest_identifier | $total_edits |\n";
    }
    echo("\n");
    echo("\n");
    echo("\n");
    echo "| QuestCode        | Total modified elements           |\n";
    echo "| ------------- |-------------|\n";
    foreach ($popularity as $quest_identifier => $total_edits) {
        if ($total_edits >= 4000) {
            echo "| $quest_identifier | ". (int)($total_edits/1000) . "k |\n";
        } else {
            echo "| $quest_identifier | $total_edits |\n";
        }
    }

    // Unset the file to call __destruct(), closing the file handle.
    $file = null; 
    fclose($outputFile);
}

main($argv[1])
?>
