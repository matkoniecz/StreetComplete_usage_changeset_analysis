<?php
require_once('../extracting_data_from_xml_line.php');

function test($input, $expected) {
    if (get_changeset_id($input) !== $expected ) {
        echo "((((((((";
        echo "\n";
        echo $input;
        echo "\n";
        echo $expected;
        echo "\n";
        echo get_changeset_id($input);
        echo "\n";
        echo "\n";
    } else {
        #echo "OK\n";
    }
}

$input = '<changeset id="50324549" created_at="2017-07-16T12:07:01Z" closed_at="2017-07-16T12:07:05Z" open="false" user="Jezze" uid="4767933" min_lat="53.6305509" min_lon="9.9126046" max_lat="53.6393257" max_lon="9.9305957" num_changes="5" comments_count="0">';
test($input, 50324549);
?>
