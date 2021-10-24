<?php
// for assumptions being made about file format, allowing to process it without
// parsing it as an XML, see extracting_data_from_xml_line.php file
require_once('extracting_data_from_xml_line.php');

function main($filename) {
    $file = new SplFileObject($filename);

    $outputFile = fopen("edits_with_all_declared_software.csv", "w") or die("Unable to open file!");
    fwrite($outputFile, "changeset_id,created_by,creation_date,changed_objects,user_id\n");

    $popularity = array();
    $changeset_header = NULL;
    while (!$file->eof()) {
        $line = trim($file->fgets());
        if ($line == "</changeset>") {
            #echo $line;
            #echo "end of a changeset with tags\n\n";
            $changeset_header = NULL;
        } elseif (str_begins($line, "<changeset")) {
            if(str_ends($line, '">')) {
                $changeset_header = $line;
                #echo "new changeset, with tags\n\n";
            } else {
                #echo "new changeset, without tags\n\n";
            }
        } else {
            if (str_begins($line, '<tag k="created_by"')) {
                $created_by = value_of_key($line, "created_by");
                $id = get_changeset_id($changeset_header);
                $count = get_changes_number($changeset_header);
                $uid = get_uid($changeset_header);
                $date = get_changeset_creation_date($changeset_header);
                fwrite($outputFile, $id . "," . '"' . $created_by . '"' . "," . $date . "," . $count . "," . $uid . "\n");
                $changeset_header = NULL;
            }
        }
    }
}

main($argv[1])
// special thanks to @Zverik for answering https://github.com/Zverik/editor-stats/issues/4 
// without this I would not expect processing such data to be feasible (changeset planet file can be read line by line)!
?>
