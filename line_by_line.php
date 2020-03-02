<?php
// special thanks to @Zverik for answering https://github.com/Zverik/editor-stats/issues/4 
// without this I would not expect processing such data to be feasible (changeset planet file can be read line by line)!


// assumptions
// changesets are formatted as follows:
// either (1)
// line begins with 
// "<changeset" and ends with "/>"
// and it is a changeset without tags
// or (2)
// line begins with '<changeset' and ends with '">'
// tags, one in each line follows
// ends with line including '</changeset>' as sole nonwhitespace text
// applies
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
            #echo "end of a changeset with tags";
            #echo "\n";
            #echo "\n";
            $changeset_header = NULL;
        } elseif (str_begins($line, "<changeset")) {
            if(str_ends($line, '">')) {
                #echo $line;
                $changeset_header = $line;
                #echo "new changeset, with tags";
                #echo "\n";
                #echo "\n";
            } else {
                #echo $line;
                #echo "new changeset, without tags";
                #echo "\n";
                #echo "\n";
            }
        } else {
            if(str_begins($line, '<tag k="created_by"')) {
                if(contains_substr($line, "StreetComplete") || contains_substr($line, "zażółć")) {
                    #echo $changeset_header;
                    #echo "\n";
                    #echo $line;
                    #echo "\n";
                    #echo "created by tag";
                    #echo "\n";    
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
                #echo "\n";
                #echo "\n";
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

function quest_tag_to_identifier($quest_tag) {
    $left_stripped = str_replace("<tag k=\"StreetComplete:quest_type\" v=\"", "", $quest_tag);
    return str_replace('"/>', '', $left_stripped);
}

// from https://www.php.net/manual/en/function.substr-compare.php
function str_begins($haystack, $needle) {
    return 0 === substr_compare($haystack, $needle, 0, strlen($needle));
}
  
function str_ends($haystack,  $needle) {
    return 0 === substr_compare($haystack, $needle, -strlen($needle));
}

function contains_substr($mainStr, $str, $loc = false) {
    if ($loc === false) return (strpos($mainStr, $str) !== false);
    if (strlen($mainStr) < strlen($str)) return false;
    if (($loc + strlen($str)) > strlen($mainStr)) return false;
    return (strcmp(substr($mainStr, $loc, strlen($str)), $str) == 0);
}

function get_changes_number($changeset_header) {
    if (preg_match("/num_changes=\"([0-9]+)\"/", $changeset_header, $matches)) {
        return (int)$matches[1];
    } else {
        return 0;
    }
}

function get_quest_type($changeset_header) {
    if (preg_match("/v=\"([^\"]+)\"/", $changeset_header, $matches)) {
        return $matches[1];
    } else {
        return NULL;
    }
}

function get_changeset_id($changeset_header) {
    if (preg_match("/ id=\"([0-9]+)\"/", $changeset_header, $matches)) {
        return (int)$matches[1];
    } else {
        return -1;
    }
}

function get_uid($changeset_header) {
    if (preg_match("/ uid=\"([0-9]+)\"/", $changeset_header, $matches)) {
        return (int)$matches[1];
    } else {
        return -1;
    }
}

function register_popularity($dict, $index, $number) {
    if (isset($dict[$index])) {
        $dict[$index] += $number;
    } else {
        $dict[$index] = $number;
    }
    return $dict;
}

main($argv[1])
?>
