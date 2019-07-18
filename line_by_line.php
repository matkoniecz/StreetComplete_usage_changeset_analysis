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
    if (preg_match("/id=\"([0-9]+)\"/", $changeset_header, $matches)) {
        return (int)$matches[1];
    } else {
        return 0;
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

$file = new SplFileObject("/media/mateusz/5bfa9dfc-ed86-4d19-ac36-78df1060707c/changesets-190708.osm");

$outputFile = fopen("output.csv", "w") or die("Unable to open file!");
fwrite($outputFile, "changeset_id" . "," . "editor" . "," . "changed_objects" . "," . "quest_type" . "\n");

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
            $popularity = register_popularity($popularity, $line, get_changes_number($changeset_header));
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
            fwrite($outputFile, $id . "," . $editor . "," . $count . "," . $type . "\n");
            #var_dump($popularity);
            #echo "\n";
            #echo "\n";
        }
    }
}

var_dump($popularity);
// Unset the file to call __destruct(), closing the file handle.
$file = null; 
fclose($outputFile);
?>
